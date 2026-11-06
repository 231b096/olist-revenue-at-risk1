"""Step 5: Cohort retention - of the customers who first bought in month X,
what share came back 1, 2, 3... months later?
"""
import matplotlib.pyplot as plt
import numpy as np

from common import ANALYSIS_END, ANALYSIS_START, load_processed, save_chart, save_csv, title

orders = load_processed("orders_fact", ["purchase_ts", "purchase_month"])
delivered = orders[orders["order_status"] == "delivered"].copy()

delivered["cohort_month"] = delivered.groupby("customer_unique_id")["purchase_month"].transform("min")
delivered["month_index"] = (
    (delivered["purchase_month"].dt.year - delivered["cohort_month"].dt.year) * 12
    + (delivered["purchase_month"].dt.month - delivered["cohort_month"].dt.month)
)
delivered = delivered[delivered["cohort_month"].between(ANALYSIS_START, ANALYSIS_END)]

active = (
    delivered.groupby(["cohort_month", "month_index"])["customer_unique_id"]
    .nunique()
    .unstack(fill_value=0)
)
cohort_size = active[0]
retention = active.divide(cohort_size, axis=0)
retention.index = retention.index.strftime("%Y-%m")
retention.insert(0, "cohort_size", cohort_size.values)

title("Cohort retention (share of each cohort active N months after first purchase)")
print(retention.iloc[:, :8].round(4).to_string())

months = [m for m in range(1, 7) if m in retention.columns]
title("Average retention across cohorts")
for m in months:
    print(f"Month {m}: {retention[m].replace(0, np.nan).mean():.2%}")
print("\nTip: cells near the bottom-right are zero because those months haven't happened yet.")

save_csv(retention, "cohort_retention", index=True)

# Month 0 is always 100%, which would wash out the colour scale, so plot months 1-12.
plot_cols = [m for m in range(1, 13) if m in retention.columns]
fig, ax = plt.subplots(figsize=(10, 6))
im = ax.imshow(retention[plot_cols].values, cmap="Blues", aspect="auto")
ax.set_xticks(range(len(plot_cols)), plot_cols)
ax.set_yticks(range(len(retention)), retention.index)
ax.set_xlabel("Months since first purchase")
ax.set_ylabel("Cohort (first purchase month)")
ax.set_title("Repeat purchase retention by cohort")
fig.colorbar(im, ax=ax, format="{x:.1%}")
save_chart(fig, "cohort_retention")
