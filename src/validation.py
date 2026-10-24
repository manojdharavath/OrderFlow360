
import pandas as pd
import re

def normalize_courier(name):
    if pd.isna(name):
        return None

    key = re.sub(r"[^a-z0-9]", "", str(name).casefold())

    aliases = {
        "bluedart": "Blue Dart",
        "delhivery": "Delhivery",
        "dtdc": "DTDC",
        "ecomexpress": "Ecom Express",
        "ekart": "Ekart",
        "gati": "Gati",
        "indiapost": "India Post",
        "shadowfax": "Shadowfax",
        "xpressbees": "XpressBees",
    }

    return aliases.get(key, str(name).strip())

def validate_orders(df, customers=None, couriers=None):
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()

    required_columns = [
        "ORDER_ID", "CUSTOMER_ID", "PRODUCT_ID",
        "UNIT_PRICE", "QUANTITY", "ORDER_DATE",
        "COURIER_NAME", "ORDER_STATUS"
    ]

    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    reasons = pd.Series("", index=df.index, dtype="object")

    def add_reason(mask, message):
        mask = mask.fillna(False)
        reasons.loc[mask] = reasons.loc[mask].apply(
            lambda current: f"{current}; {message}" if current else message
        )

    # Required identifiers
    for col in ["ORDER_ID", "CUSTOMER_ID", "PRODUCT_ID"]:
        values = df[col].astype("string").str.strip()
        add_reason(values.isna() | values.eq(""), f"Missing {col}")

    # Numeric validation
    price = pd.to_numeric(df["UNIT_PRICE"], errors="coerce")
    quantity = pd.to_numeric(df["QUANTITY"], errors="coerce")

    add_reason(price.isna() | price.le(0), "Invalid UNIT_PRICE")
    add_reason(
        quantity.isna() | quantity.le(0) | quantity.mod(1).ne(0),
        "Invalid QUANTITY"
    )

    # Date validation
    order_date = pd.to_datetime(
        df["ORDER_DATE"], errors="coerce", format="mixed"
    )
    add_reason(order_date.isna(), "Invalid ORDER_DATE")

    shipped_date = pd.to_datetime(
        df["SHIPPED_DATE"], errors="coerce", format="mixed"
    ) if "SHIPPED_DATE" in df.columns else pd.Series(pd.NaT, index=df.index)

    delivery_date = pd.to_datetime(
        df["DELIVERY_DATE"], errors="coerce", format="mixed"
    ) if "DELIVERY_DATE" in df.columns else pd.Series(pd.NaT, index=df.index)

    add_reason(
        shipped_date.notna() & (shipped_date < order_date),
        "SHIPPED_DATE before ORDER_DATE"
    )
    add_reason(
        delivery_date.notna() & (delivery_date < order_date),
        "DELIVERY_DATE before ORDER_DATE"
    )
    add_reason(
        shipped_date.notna() & delivery_date.notna()
        & (delivery_date < shipped_date),
        "DELIVERY_DATE before SHIPPED_DATE"
    )

    # Exact duplicate detection
    add_reason(df.duplicated(keep="first"), "Duplicate record")

    # Customer master validation
    if customers is not None:
        customer_ids = set(
            customers["CUSTOMER_ID"].dropna().astype(str).str.strip()
        )
        order_customer_ids = df["CUSTOMER_ID"].astype("string").str.strip()

        add_reason(
            order_customer_ids.notna()
            & ~order_customer_ids.isin(customer_ids),
            "CUSTOMER_ID not found in customer master"
        )

    # Normalize courier names and validate against master data
    if "COURIER_NAME" in df.columns:
        df["COURIER_NAME"] = df["COURIER_NAME"].apply(normalize_courier)

    if couriers is not None:
        courier_names = set(
            couriers["COURIER_NAME"].dropna().apply(normalize_courier)
        )
        order_couriers = df["COURIER_NAME"]

        add_reason(
            order_couriers.notna()
            & ~order_couriers.isin(courier_names),
            "COURIER_NAME not found in courier master"
        )

    # Split valid and rejected records
    rejected_mask = reasons.ne("")
    rejected = df.loc[rejected_mask].copy()
    rejected["REJECTION_REASON"] = reasons.loc[rejected_mask]
    valid = df.loc[~rejected_mask].copy()

    return valid, rejected
