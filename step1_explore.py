"""Step 1: Understand the raw data before touching it.

Questions this answers:
  - How big is each table and what is one row (the "grain")?
  - Where are the missing values?
  - Is customer_id really one per customer? (Spoiler: no.)
"""
from common import RAW_FILES, load_raw, title

KEYS = {
    "customers": "customer_id",
    "orders": "order_id",
    "products": "product_id",
    "sellers": "seller_id",
}

for name in RAW_FILES:
    df = load_raw(name)
    title(f"{name}: {len(df):,} rows x {df.shape[1]} columns")
    print("Columns:", ", ".join(df.columns))
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print("Missing values:")
        for col, n in nulls.items():
            print(f"  {col}: {n:,} ({n / len(df):.1%})")
    if name in KEYS:
        dupes = df[KEYS[name]].duplicated().sum()
        print(f"Duplicate {KEYS[name]}s: {dupes:,}")

title("Key data-quality findings")
customers = load_raw("customers")
orders = load_raw("orders")
reviews = load_raw("reviews")

print(f"customer_id values:        {customers['customer_id'].nunique():,}")
print(f"customer_unique_id values: {customers['customer_unique_id'].nunique():,}")
print("-> customer_id is created per ORDER. Use customer_unique_id for the real person.")

print("\nOrder status breakdown:")
print(orders["order_status"].value_counts().to_string())

per_order = reviews.groupby("order_id").size()
print(f"\nOrders with more than one review: {(per_order > 1).sum():,}")
print("-> Reviews must be aggregated per order before joining, or revenue gets double-counted.")

purchase = orders["order_purchase_timestamp"]
print(f"\nPurchase dates range from {purchase.min()} to {purchase.max()}")
print("Orders per month (look for thin months at the start and end):")
print(orders.assign(month=purchase.str[:7]).groupby("month").size().to_string())
