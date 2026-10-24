
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

def load_csv(filename):
    file_path = RAW_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    df = pd.read_csv(file_path)
    print(f"Loaded {filename}: {len(df)} rows")

    return df

def load_source_data():
    orders = load_csv("order_transactions_v3.csv")
    dirty_orders = load_csv("order_transactions_dirty_v3.csv")
    customers = load_csv("customer_master_orders_v3.csv")
    couriers = load_csv("courier_sla_master_v3.csv")

    return orders, dirty_orders, customers, couriers
