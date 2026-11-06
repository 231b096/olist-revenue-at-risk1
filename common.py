"""Shared paths and helpers used by every step script."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

# The first and last few months of Olist data are incomplete, so trends use this window.
ANALYSIS_START = "2017-01-01"
ANALYSIS_END = "2018-08-31"

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def load_raw(name):
    # utf-8-sig strips the hidden BOM character some Kaggle CSVs have in the first header
    return pd.read_csv(RAW / RAW_FILES[name], encoding="utf-8-sig")


def load_processed(name, date_cols=()):
    return pd.read_csv(PROCESSED / f"{name}.csv", parse_dates=list(date_cols))


def save_csv(df, name, folder=OUTPUTS, index=False):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    df.to_csv(path, index=index)
    print(f"  saved {path.relative_to(ROOT)}")


def save_chart(fig, name):
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  saved {path.relative_to(ROOT)}")


def title(text):
    print(f"\n=== {text} ===")
