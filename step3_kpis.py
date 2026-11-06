"""Step 3: Headline KPIs and monthly trend - the 'how is the business doing' view."""
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

from common import ANALYSIS_END, ANALYSIS_START, load_processed, save_chart, save_csv, title

orders = load_processed("orders_fact", ["purchase_ts", "purchase_month"])
delivered = orders[orders["order_status"] == "delivered"]
customers = load_processed("customer_summary")

kpis = {
    "Total revenue (delivered)": delivered["order_revenue"].sum(),
    "Delivered orders": len(delivered),
    "Unique customers": len(customers),
    "Average order value (AOV)": delivered["order_revenue"].mean(),
    "Orders per customer": len(delivered) / len(customers),
    "Repeat customer rate": (customers["n_orders"] > 1).mean(),
    "Late delivery rate": delivered["is_late"].mean(),
    "Average review score": delivered["review_score"].mean(),
    "Cancellation rate (all orders)": (orders["order_status"] == "canceled").mean(),
}

title("Headline KPIs")
for name, value in kpis.items():
    if "rate" in name:
        print(f"{name:32s} {value:.1%}")
    else:
        print(f"{name:32s} {value:,.2f}")

in_window = delivered[delivered["purchase_ts"].between(ANALYSIS_START, ANALYSIS_END)]
monthly = (
    in_window.groupby("purchase_month")
    .agg(
        revenue=("order_revenue", "sum"),
        orders=("order_id", "count"),
        customers=("customer_unique_id", "nunique"),
        aov=("order_revenue", "mean"),
        late_rate=("is_late", "mean"),
        avg_review=("review_score", "mean"),
    )
    .reset_index()
)
monthly["revenue_mom_growth"] = monthly["revenue"].pct_change()

title(f"Monthly trend {ANALYSIS_START} to {ANALYSIS_END}")
print(monthly.round(3).to_string(index=False))

save_csv(pd.DataFrame(list(kpis.items()), columns=["kpi", "value"]), "kpis")
save_csv(monthly, "monthly_trend")

fig, ax1 = plt.subplots(figsize=(10, 4))
ax1.bar(monthly["purchase_month"], monthly["revenue"], width=20, color="#4C78A8")
ax1.set_ylabel("Revenue (R$)")
ax2 = ax1.twinx()
ax2.plot(monthly["purchase_month"], monthly["late_rate"], color="#E45756", marker="o")
ax2.set_ylabel("Late delivery rate", color="#E45756")
ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
ax1.set_title("Monthly revenue vs late delivery rate")
save_chart(fig, "monthly_trend")
