
from pathlib import Path
import pandas as pd
from ingestion import load_source_data
from validation import validate_orders
from transformation import transform_orders

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REJECTED_DIR = BASE_DIR / "data" / "rejected"

def run_pipeline():
    orders, dirty_orders, customers, couriers = load_source_data()

    # 1. Combine transaction datasets
    all_orders = pd.concat([orders, dirty_orders], ignore_index=True)
    total_records = len(all_orders)

    print("\n========== ORDERFLOW360 PIPELINE ==========")
    print(f"Total input records: {total_records}")

    # 2. Validate transactions
    print("\n--- Validating transactions ---")
    valid_orders, rejected_orders = validate_orders(
        all_orders,
        customers=customers,
        couriers=couriers
    )

    # 3. Transform valid transactions
    print("\n--- Transforming valid transactions ---")
    clean_orders = transform_orders(valid_orders)

    # 4. Prepare output directories
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    # 5. Save pipeline outputs
    clean_orders.to_csv(
        PROCESSED_DIR / "orders_clean.csv",
        index=False
    )
    rejected_orders.to_csv(
        REJECTED_DIR / "orders_rejected.csv",
        index=False
    )
    customers.to_csv(
        PROCESSED_DIR / "customers.csv",
        index=False
    )
    couriers.to_csv(
        PROCESSED_DIR / "couriers.csv",
        index=False
    )

    # 6. Display results
    valid_count = len(clean_orders)
    rejected_count = len(rejected_orders)

    print("\n========== DATA QUALITY SUMMARY ==========")
    print(f"Total input records: {total_records}")
    print(f"Valid records:       {valid_count}")
    print(f"Rejected records:    {rejected_count}")

    if valid_count + rejected_count == total_records:
        print("Reconciliation:      PASS")
    else:
        print("Reconciliation:      FAIL")

    if not rejected_orders.empty:
        print("\n========== REJECTION REASONS ==========")
        print(
            rejected_orders["REJECTION_REASON"]
            .str.split("; ")
            .explode()
            .value_counts()
            .to_string()
        )

    print("\n========== OUTPUT FILES ==========")
    print(f"Clean orders:    {PROCESSED_DIR / 'orders_clean.csv'}")
    print(f"Customers:       {PROCESSED_DIR / 'customers.csv'}")
    print(f"Couriers:        {PROCESSED_DIR / 'couriers.csv'}")
    print(f"Rejected orders: {REJECTED_DIR / 'orders_rejected.csv'}")

    return {
        "orders": clean_orders,
        "customers": customers,
        "couriers": couriers,
        "rejected_orders": rejected_orders,
    }

if __name__ == "__main__":
    run_pipeline()
    