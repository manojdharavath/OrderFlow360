
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

FILES = [
    "order_transactions_v3.csv",
    "order_transactions_dirty_v3.csv",
    "customer_master_orders_v3.csv",
    "courier_sla_master_v3.csv",
]

def profile_file(filename):
    path = RAW_DIR / filename

    if not path.exists():
        print(f"File not found: {filename}")
        return

    df = pd.read_csv(path)

    print("\n" + "=" * 50)
    print(f"FILE: {filename}")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Duplicate rows: {df.duplicated().sum()}")

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nMissing values:")
    print(df.isnull().sum().to_string())

    print("\nSample records:")
    print(df.head(3).to_string(index=False))

def main():
    for filename in FILES:
        profile_file(filename)

if __name__ == "__main__":
    main()
