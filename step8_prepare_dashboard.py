"""Step 8 prep: combine everything into ONE flat file for Tableau / Power BI.

One row per order, with the customer's RFM segment and the first-order
root-cause columns added. One file means no relationships to set up.
"""
import pandas as pd

from common import OUTPUTS, ROOT, load_processed, title

orders = load_processed("orders_fact")
rfm = pd.read_csv(OUTPUTS / "rfm_customers.csv")
first = pd.read_csv(OUTPUTS / "first_orders.csv")

rfm_cols = ["customer_unique_id", "recency_days", "frequency", "monetary",
            "R", "F", "M", "RFM_code", "segment"]
first_cols = ["order_id", "delay_bucket", "freight_bucket", "has_repeat", "low_review"]

# Left joins keep every order: customers with no delivered order get no segment,
# and only first orders (in the observation window) get has_repeat / delay_bucket.
dashboard = (
    orders.merge(rfm[rfm_cols], on="customer_unique_id", how="left")
    .merge(first[first_cols], on="order_id", how="left")
)
assert len(dashboard) == len(orders), "Merge duplicated rows"

out = ROOT / "dashboard" / "dashboard_data.csv"
out.parent.mkdir(exist_ok=True)
dashboard.to_csv(out, index=False)

title("Dashboard file ready")
print(f"{len(dashboard):,} rows x {dashboard.shape[1]} columns -> {out.relative_to(ROOT)}")
print("Columns:", ", ".join(dashboard.columns))
