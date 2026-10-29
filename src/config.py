"""Central configuration: paths, file names and analysis constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
DB_PATH = ROOT / "data" / "olist.db"

# table name in the database  ->  CSV file name in data/raw/
CSV_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# columns that hold timestamps, per table (normalised to 'YYYY-MM-DD HH:MM:SS')
DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}

# The source data only has complete months inside this window
ANALYSIS_START = "2017-01"
ANALYSIS_END = "2018-08"

# Statuses excluded from revenue metrics
EXCLUDED_STATUSES = ("canceled", "unavailable")

# Visual identity used by every chart / the dashboard
PALETTE = {
    "primary": "#1F4E79",
    "accent": "#F28E2B",
    "good": "#2E8B57",
    "bad": "#C0392B",
    "neutral": "#8A94A6",
    "light": "#EEF2F7",
    "ink": "#1B2430",
}
