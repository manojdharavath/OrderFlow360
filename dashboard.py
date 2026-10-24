
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------- CONFIGURATION --------------------
BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REJECTED_DIR = BASE_DIR / "data" / "rejected"

st.set_page_config(
    page_title="OrderFlow360 | Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- THEME --------------------
st.markdown("""
<style>
.main-header {
    font-size: 2.2rem;
    font-weight: 750;
    letter-spacing: -1px;
}
.sub-header {
    color: #8b95a5;
    font-size: 1rem;
}
div[data-testid="stMetric"] {
    background: rgba(128,128,128,0.07);
    border: 1px solid rgba(128,128,128,0.18);
    padding: 16px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# -------------------- DATA LOADING --------------------
@st.cache_data
def load_data():
    orders = pd.read_csv(PROCESSED_DIR / "orders_clean.csv")
    customers = pd.read_csv(PROCESSED_DIR / "customers.csv")
    couriers = pd.read_csv(PROCESSED_DIR / "couriers.csv")
    rejected = pd.read_csv(REJECTED_DIR / "orders_rejected.csv")

    for df in [orders, customers, couriers, rejected]:
        df.columns = df.columns.str.strip().str.upper()

    for col in [
        "ORDER_DATE", "SHIPPED_DATE",
        "DELIVERY_DATE", "LAST_UPDATED_TS"
    ]:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors="coerce")

    for col in ["UNIT_PRICE", "QUANTITY", "ORDER_VALUE",
                "DELIVERY_DURATION_DAYS"]:
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce")

    if "ORDER_VALUE" not in orders.columns:
        if {"UNIT_PRICE", "QUANTITY"}.issubset(orders.columns):
            orders["ORDER_VALUE"] = orders["UNIT_PRICE"] * orders["QUANTITY"]
        else:
            orders["ORDER_VALUE"] = 0

    if "ORDER_STATUS" in orders.columns:
        orders["ORDER_STATUS"] = (
            orders["ORDER_STATUS"].astype("string").str.strip().str.title()
        )

    if "COURIER_NAME" in orders.columns:
        orders["COURIER_NAME"] = orders["COURIER_NAME"].astype("string").str.strip()

    if "COURIER_NAME" in couriers.columns:
        couriers["COURIER_NAME"] = couriers["COURIER_NAME"].astype("string").str.strip()

    if "SLA_DAYS" in couriers.columns:
        couriers["SLA_DAYS"] = pd.to_numeric(couriers["SLA_DAYS"], errors="coerce")

    # Use shipment-to-delivery time when both dates are available.
    if {"SHIPPED_DATE", "DELIVERY_DATE"}.issubset(orders.columns):
        orders["TRANSIT_DAYS"] = (
            orders["DELIVERY_DATE"] - orders["SHIPPED_DATE"]
        ).dt.total_seconds() / 86400
    elif "DELIVERY_DURATION_DAYS" in orders.columns:
        orders["TRANSIT_DAYS"] = orders["DELIVERY_DURATION_DAYS"]
    else:
        orders["TRANSIT_DAYS"] = float("nan")

    # Attach courier SLA reference data.
    if {"COURIER_NAME", "SLA_DAYS"}.issubset(couriers.columns):
        orders = orders.merge(
            couriers[["COURIER_NAME", "SLA_DAYS"]].drop_duplicates("COURIER_NAME"),
            on="COURIER_NAME",
            how="left"
        )
    else:
        orders["SLA_DAYS"] = float("nan")

    delivered = orders["ORDER_STATUS"].eq("Delivered") if "ORDER_STATUS" in orders.columns else pd.Series(False, index=orders.index)

    # SLA compliance is evaluated only for delivered orders with known duration and SLA.
    orders["SLA_EVALUABLE"] = (
        delivered
        & orders["TRANSIT_DAYS"].notna()
        & orders["SLA_DAYS"].notna()
        & orders["TRANSIT_DAYS"].ge(0)
    )
    orders["ON_TIME"] = (
        orders["SLA_EVALUABLE"]
        & orders["TRANSIT_DAYS"].le(orders["SLA_DAYS"])
    )

    return orders, customers, couriers, rejected


try:
    orders, customers, couriers, rejected = load_data()
except FileNotFoundError as exc:
    st.error(f"Required data file not found: {exc}")
    st.info("Check that the processed and rejected CSV files exist in the expected folders.")
    st.stop()
except Exception as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()


# -------------------- HELPERS --------------------
def money(value):
    return f"₹{value:,.2f}"

def percent(numerator, denominator):
    return f"{numerator / denominator * 100:.1f}%" if denominator else "N/A"

def show_download(df, filename, label):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv"
    )

def chart_if_data(df, x, y, title, chart_type="bar", color=None):
    if df.empty or x not in df.columns or y not in df.columns:
        st.info(f"Not enough data available for {title.lower()}.")
        return
    if chart_type == "line":
        fig = px.line(df, x=x, y=y, title=title, markers=True, color=color)
    else:
        fig = px.bar(df, x=x, y=y, title=title, color=color)
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)


# -------------------- SIDEBAR --------------------
st.sidebar.markdown("## 📦 OrderFlow360")
st.sidebar.caption("E-Commerce Fulfillment Analytics")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    [
        "Business Overview",
        "Delivery Performance",
        "Sales & Orders",
        "Data Quality",
        "Order Explorer"
    ]
)

filtered = orders.copy()

if "ORDER_DATE" in filtered.columns:
    valid_dates = filtered["ORDER_DATE"].dropna()
    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        date_range = st.sidebar.date_input(
            "Order date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered = filtered[
                filtered["ORDER_DATE"].dt.date.between(start_date, end_date)
            ]

for column, label in [
    ("COURIER_NAME", "Courier"),
    ("CATEGORY", "Category"),
    ("ORDER_STATUS", "Order status"),
    ("PAYMENT_MODE", "Payment mode")
]:
    if column in filtered.columns:
        values = sorted(filtered[column].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect(
            label,
            values,
            default=values,
            key=f"filter_{column}"
        )
        filtered = filtered[filtered[column].astype(str).isin(selected)]

st.sidebar.divider()
st.sidebar.caption(f"Loaded order records: {len(orders):,}")
st.sidebar.caption(f"Filtered order records: {len(filtered):,}")
if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()


# -------------------- HEADER --------------------
st.markdown('<div class="main-header">📦 OrderFlow360</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">E-Commerce Order Fulfillment & Delivery Analytics</div>',
    unsafe_allow_html=True
)
st.divider()


# -------------------- PAGE 1: OVERVIEW --------------------
if page == "Business Overview":
    st.subheader("Business Overview")
    total_orders = len(filtered)
    total_value = filtered["ORDER_VALUE"].sum()
    delivered_count = int(filtered["ORDER_STATUS"].eq("Delivered").sum()) if "ORDER_STATUS" in filtered.columns else 0
    cancelled_count = int(filtered["ORDER_STATUS"].eq("Cancelled").sum()) if "ORDER_STATUS" in filtered.columns else 0
    returned_count = int(filtered["ORDER_STATUS"].eq("Returned").sum()) if "ORDER_STATUS" in filtered.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders", f"{total_orders:,}")
    c2.metric("Total Order Value", money(total_value))
    c3.metric("Delivered Orders", f"{delivered_count:,}")
    c4.metric("Cancellation Rate", percent(cancelled_count, total_orders))
    c5.metric("Return Rate", percent(returned_count, total_orders))

    st.caption("Order value is UNIT_PRICE × QUANTITY. It represents order value, not necessarily collected revenue.")
    left, right = st.columns(2)

    with left:
        if "ORDER_STATUS" in filtered.columns:
            status_counts = (
                filtered["ORDER_STATUS"].fillna("Unknown")
                .value_counts().rename_axis("ORDER_STATUS")
                .reset_index(name="ORDERS")
            )
            if not status_counts.empty:
                fig = px.pie(
                    status_counts, names="ORDER_STATUS", values="ORDERS",
                    title="Order Status Distribution", hole=0.45
                )
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

    with right:
        if "ORDER_DATE" in filtered.columns:
            monthly = filtered.dropna(subset=["ORDER_DATE"]).copy()
            monthly["MONTH"] = monthly["ORDER_DATE"].dt.to_period("M").astype(str)
            monthly = monthly.groupby("MONTH", as_index=False).agg(
                ORDERS=("ORDER_ID", "count") if "ORDER_ID" in monthly.columns else ("ORDER_VALUE", "size"),
                ORDER_VALUE=("ORDER_VALUE", "sum")
            )
            chart_if_data(monthly, "MONTH", "ORDERS", "Monthly Order Trend", "line")

    if "CATEGORY" in filtered.columns:
        category_sales = filtered.groupby("CATEGORY", dropna=False, as_index=False)["ORDER_VALUE"].sum()
        category_sales = category_sales.sort_values("ORDER_VALUE", ascending=False)
        chart_if_data(category_sales, "CATEGORY", "ORDER_VALUE", "Order Value by Category")


# -------------------- PAGE 2: DELIVERY --------------------
elif page == "Delivery Performance":
    st.subheader("Delivery & Courier Performance")

    if "ORDER_STATUS" not in filtered.columns:
        st.warning("Order status is unavailable in the dataset.")
    else:
        delivered = filtered[filtered["ORDER_STATUS"].eq("Delivered")].copy()
        evaluable = delivered[delivered["SLA_EVALUABLE"]]
        avg_transit = delivered["TRANSIT_DAYS"].dropna().mean()
        on_time_rate = (
            evaluable["ON_TIME"].mean() * 100 if not evaluable.empty else None
        )
        delayed = int((~evaluable["ON_TIME"]).sum()) if not evaluable.empty else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Delivered Orders", f"{len(delivered):,}")
        c2.metric("Avg. Transit Days", f"{avg_transit:.2f}" if pd.notna(avg_transit) else "N/A")
        c3.metric("On-Time SLA Rate", f"{on_time_rate:.1f}%" if on_time_rate is not None else "N/A")
        c4.metric("SLA-Evaluable Delays", f"{delayed:,}" if not evaluable.empty else "N/A")

        st.caption("Transit time = delivery date − shipped date. SLA compliance is calculated only for delivered orders with valid transit duration and a matching courier SLA. Unknown SLA records are excluded.")

        if not delivered.empty and "COURIER_NAME" in delivered.columns:
            courier_stats = delivered.groupby("COURIER_NAME", dropna=False).agg(
                DELIVERED_ORDERS=("ORDER_ID", "count") if "ORDER_ID" in delivered.columns else ("ORDER_VALUE", "size"),
                AVG_TRANSIT_DAYS=("TRANSIT_DAYS", "mean"),
                SLA_EVALUABLE=("SLA_EVALUABLE", "sum"),
                ON_TIME_ORDERS=("ON_TIME", "sum")
            ).reset_index()
            courier_stats["ON_TIME_RATE_PCT"] = (
                courier_stats["ON_TIME_ORDERS"] / courier_stats["SLA_EVALUABLE"].replace(0, float("nan")) * 100
            )
            left, right = st.columns(2)
            with left:
                chart_if_data(courier_stats, "COURIER_NAME", "DELIVERED_ORDERS", "Delivered Orders by Courier")
            with right:
                chart_if_data(courier_stats, "COURIER_NAME", "AVG_TRANSIT_DAYS", "Average Transit Days by Courier")
            st.markdown("#### Courier Performance Details")
            st.dataframe(courier_stats, use_container_width=True, hide_index=True)

        st.markdown("#### Delivered Orders Missing SLA Evaluation")
        missing_sla = delivered[~delivered["SLA_EVALUABLE"]]
        if missing_sla.empty:
            st.success("All filtered delivered orders have a valid transit duration and matched courier SLA.")
        else:
            st.info(f"{len(missing_sla):,} delivered orders cannot be evaluated against SLA.")
            st.dataframe(missing_sla, use_container_width=True, hide_index=True)
            show_download(missing_sla, "orders_missing_sla.csv", "Download unevaluable orders")


# -------------------- PAGE 3: SALES & ORDERS --------------------
elif page == "Sales & Orders":
    st.subheader("Sales & Order Analysis")
    total_qty = filtered["QUANTITY"].sum() if "QUANTITY" in filtered.columns else 0
    average_order_value = filtered["ORDER_VALUE"].mean() if not filtered.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Order Value", money(filtered["ORDER_VALUE"].sum()))
    c2.metric("Total Units", f"{total_qty:,.0f}")
    c3.metric("Average Order Value", money(average_order_value))

    left, right = st.columns(2)
    with left:
        if "CATEGORY" in filtered.columns:
            category = filtered.groupby("CATEGORY", dropna=False, as_index=False).agg(
                ORDER_VALUE=("ORDER_VALUE", "sum")
            ).sort_values("ORDER_VALUE", ascending=False)
            chart_if_data(category, "CATEGORY", "ORDER_VALUE", "Order Value by Category")
    with right:
        if "PAYMENT_MODE" in filtered.columns:
            payment = filtered["PAYMENT_MODE"].fillna("Unknown").value_counts().rename_axis("PAYMENT_MODE").reset_index(name="ORDERS")
            chart_if_data(payment, "PAYMENT_MODE", "ORDERS", "Orders by Payment Mode")

    if "PRODUCT_NAME" in filtered.columns:
        st.markdown("#### Top 10 Products by Order Value")
        products = filtered.groupby("PRODUCT_NAME", dropna=False, as_index=False).agg(
            ORDER_VALUE=("ORDER_VALUE", "sum"),
            UNITS=("QUANTITY", "sum") if "QUANTITY" in filtered.columns else ("ORDER_VALUE", "count")
        ).sort_values("ORDER_VALUE", ascending=False).head(10)
        chart_if_data(products, "PRODUCT_NAME", "ORDER_VALUE", "Top Products")


# -------------------- PAGE 4: DATA QUALITY --------------------
elif page == "Data Quality":
    st.subheader("Data Quality & Pipeline Monitoring")
    total_input = len(orders) + len(rejected)
    valid_count = len(orders)
    rejected_count = len(rejected)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clean Order Records", f"{valid_count:,}")
    c2.metric("Rejected Records", f"{rejected_count:,}")
    c3.metric("Acceptance Rate", percent(valid_count, total_input))
    c4.metric("Rejection Rate", percent(rejected_count, total_input))

    if total_input and valid_count + rejected_count == total_input:
        st.success(f"Reconciliation PASS: {valid_count:,} + {rejected_count:,} = {total_input:,} input records.")
    else:
        st.warning("Reconciliation does not match. Verify the pipeline outputs and whether the input datasets overlap.")

    if "REJECTION_REASON" in rejected.columns:
        reason_counts = (
            rejected["REJECTION_REASON"].fillna("Unspecified")
            .astype(str).str.split("; ").explode()
            .value_counts().rename_axis("REJECTION_REASON")
            .reset_index(name="RECORD_COUNT")
        )
        chart_if_data(reason_counts, "REJECTION_REASON", "RECORD_COUNT", "Rejection Reasons")
        st.markdown("#### Rejection Reason Summary")
        st.dataframe(reason_counts, use_container_width=True, hide_index=True)
    else:
        st.warning("REJECTION_REASON column was not found in the rejected data.")

    st.markdown("#### Rejected Records")
    st.dataframe(rejected, use_container_width=True, hide_index=True)
    show_download(rejected, "orders_rejected.csv", "Download rejected records")

    st.markdown("#### Master Data Overview")
    m1, m2 = st.columns(2)
    m1.metric("Customer Master Records", f"{len(customers):,}")
    m2.metric("Courier Master Records", f"{len(couriers):,}")
    with st.expander("View courier SLA master"):
        st.dataframe(couriers, use_container_width=True, hide_index=True)
    with st.expander("View customer master"):
        st.dataframe(customers, use_container_width=True, hide_index=True)


# -------------------- PAGE 5: ORDER EXPLORER --------------------
elif page == "Order Explorer":
    st.subheader("Order Explorer")
    st.caption("Use the sidebar filters to narrow down the records.")
    st.write(f"Showing **{len(filtered):,}** matching records.")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    show_download(filtered, "filtered_orders.csv", "Download filtered orders")

    if "ORDER_STATUS" in filtered.columns:
        st.markdown("#### Status Summary")
        summary = filtered["ORDER_STATUS"].fillna("Unknown").value_counts().rename_axis("ORDER_STATUS").reset_index(name="ORDERS")
        st.dataframe(summary, use_container_width=True, hide_index=True)

st.divider()
st.caption("OrderFlow360 | E-Commerce Order Fulfillment Analytics")
