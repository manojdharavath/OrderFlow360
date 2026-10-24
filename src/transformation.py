
import pandas as pd

def transform_orders(df):
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()

    # Standardize text columns
    text_columns = [
        "ORDER_ID", "CUSTOMER_ID", "PRODUCT_ID",
        "PRODUCT_NAME", "CATEGORY", "COURIER_NAME",
        "ORDER_STATUS", "PAYMENT_MODE"
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # Standardize order status
    if "ORDER_STATUS" in df.columns:
        status_map = {
            "DELIVERED": "Delivered",
            "CANCELLED": "Cancelled",
            "CANCELED": "Cancelled",
            "RETURNED": "Returned",
            "IN TRANSIT": "In Transit",
            "IN_TRANSIT": "In Transit",
            "SHIPPED": "Shipped",
            "PROCESSING": "Processing",
        }
        normalized = df["ORDER_STATUS"].str.upper().str.replace(
            r"[\s-]+", "_", regex=True
        )
        df["ORDER_STATUS"] = normalized.map(
            lambda value: (
                status_map.get(value.replace("_", " "), status_map.get(value, value.title()))
                if pd.notna(value) else value
            )
        )

    # Convert numeric fields
    for col in ["UNIT_PRICE", "QUANTITY"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert date fields; invalid values become NaT
    for col in [
        "ORDER_DATE", "SHIPPED_DATE",
        "DELIVERY_DATE", "LAST_UPDATED_TS"
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col], errors="coerce", format="mixed"
            )

    # Calculate delivery duration when both dates exist
    if {"SHIPPED_DATE", "DELIVERY_DATE"}.issubset(df.columns):
        df["DELIVERY_DURATION_DAYS"] = (
            df["DELIVERY_DATE"] - df["SHIPPED_DATE"]
        ).dt.total_seconds() / 86400

    # Calculate order value
    if {"UNIT_PRICE", "QUANTITY"}.issubset(df.columns):
        df["ORDER_VALUE"] = df["UNIT_PRICE"] * df["QUANTITY"]

    return df
