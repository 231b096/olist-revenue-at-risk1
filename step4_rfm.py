"""Step 4: RFM segmentation - group customers by how they behave.

R = Recency   : days since last purchase (lower is better)
F = Frequency : number of orders (higher is better)
M = Monetary  : total spend (higher is better)
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

from common import load_processed, save_chart, save_csv, title

customers = load_processed("customer_summary", ["first_purchase_ts", "last_purchase_ts"])

# Measure recency from the day after the last order in the data, not from today,
# because the dataset ends in 2018.
snapshot = customers["last_purchase_ts"].max() + pd.Timedelta(days=1)
rfm = customers.assign(
    recency_days=(snapshot - customers["last_purchase_ts"]).dt.days,
    frequency=customers["n_orders"],
    monetary=customers["total_revenue"],
)

# R and M: split customers into 5 equal-sized groups (quintiles).
# rank(method="first") breaks ties so qcut always gets 5 distinct bins.
rfm["R"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

# F: most Olist customers order once, so quintiles would put identical customers in
# different groups. Business rules are more honest here.
rfm["F"] = np.select([rfm["frequency"] >= 3, rfm["frequency"] == 2], [5, 3], default=1)

# Rules are checked top to bottom; the first match wins.
rules = [
    ("Champions", (rfm["R"] >= 4) & (rfm["F"] >= 3) & (rfm["M"] >= 4)),
    ("Loyal", rfm["F"] >= 3),
    ("New Big Spenders", (rfm["R"] >= 4) & (rfm["M"] >= 4)),
    ("Recent", rfm["R"] >= 4),
    ("At Risk", (rfm["R"] <= 2) & (rfm["M"] >= 4)),
    ("Needs Attention", rfm["R"] == 3),
    ("Lost", rfm["R"] <= 2),
]
rfm["segment"] = np.select([cond for _, cond in rules], [name for name, _ in rules], default="Other")
rfm["RFM_code"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

summary = (
    rfm.groupby("segment")
    .agg(
        customers=("customer_unique_id", "count"),
        revenue=("monetary", "sum"),
        avg_recency_days=("recency_days", "mean"),
        avg_orders=("frequency", "mean"),
        avg_spend=("monetary", "mean"),
        avg_review=("avg_review_score", "mean"),
    )
    .reindex([name for name, _ in rules])
    .dropna(subset=["customers"])
)
summary["pct_customers"] = summary["customers"] / summary["customers"].sum()
summary["pct_revenue"] = summary["revenue"] / summary["revenue"].sum()

title(f"RFM segments (snapshot date {snapshot.date()})")
print(summary.round(2).to_string())

save_csv(rfm, "rfm_customers")
save_csv(summary, "rfm_segment_summary", index=True)

fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(len(summary))
ax.bar(x - 0.2, summary["pct_customers"], 0.4, label="% of customers", color="#4C78A8")
ax.bar(x + 0.2, summary["pct_revenue"], 0.4, label="% of revenue", color="#F58518")
ax.set_xticks(x, summary.index, rotation=20)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_title("Share of customers vs share of revenue by segment")
ax.legend()
save_chart(fig, "rfm_segments")
