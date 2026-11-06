"""Step 6: Root cause - why don't customers come back?

Hypothesis chain we test:
  late delivery  ->  bad review  ->  customer never buys again

We look only at each customer's FIRST delivered order, because that experience is
what decides whether they return.
"""
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

from common import load_processed, save_chart, save_csv, title

OBSERVATION_DAYS = 180   # a customer needs time to come back before we call them "not repeat"
MIN_ORDERS_PER_GROUP = 300

orders = load_processed("orders_fact", ["purchase_ts"])
customers = load_processed("customer_summary")

first = orders[orders["delivered_order_number"] == 1].merge(
    customers[["customer_unique_id", "n_orders"]], on="customer_unique_id"
)
first["has_repeat"] = (first["n_orders"] > 1).astype(int)
first["low_review"] = (first["review_score"] <= 2).astype(int)

# Fairness check: someone who first bought last week hasn't had a chance to return.
cutoff = orders["purchase_ts"].max() - pd.Timedelta(days=OBSERVATION_DAYS)
first = first[first["purchase_ts"] <= cutoff]
print(f"First orders analysed: {len(first):,} (placed on or before {cutoff.date()})")
print(f"Overall repeat rate: {first['has_repeat'].mean():.2%}")


def compare(df, by, label):
    out = (
        df.groupby(by, observed=True)
        .agg(
            orders=("order_id", "count"),
            avg_review=("review_score", "mean"),
            low_review_rate=("low_review", "mean"),
            repeat_rate=("has_repeat", "mean"),
            late_rate=("is_late", "mean"),
        )
        .reset_index()
    )
    title(label)
    print(out.round(4).to_string(index=False))
    return out


late = compare(first.assign(delivery=first["is_late"].map({0: "On time", 1: "Late"})),
               "delivery", "A. Late vs on-time first orders")

delay_bins = [-1000, -8, -1, 0, 3, 7, 1000]
delay_labels = ["Early 8+ days", "Early 1-7 days", "On estimate day", "Late 1-3 days",
                "Late 4-7 days", "Late 8+ days"]
first["delay_bucket"] = pd.cut(first["days_vs_estimate"], delay_bins, labels=delay_labels)
delay = compare(first, "delay_bucket", "B. How late? (days vs promised date)")

review = compare(first.dropna(subset=["review_score"]).assign(
    review=first["review_score"].round().astype("Int64")), "review",
    "C. Review score of first order vs repeat rate")

first["freight_bucket"] = pd.cut(first["freight_share"], [0, 0.1, 0.2, 0.3, 1.0],
                                 labels=["<10%", "10-20%", "20-30%", "30%+"], include_lowest=True)
freight = compare(first, "freight_bucket", "D. Freight as share of order value")

category = compare(first, "category", "E. Product categories")
category = category[category["orders"] >= MIN_ORDERS_PER_GROUP].sort_values("repeat_rate")
title(f"E2. Categories with at least {MIN_ORDERS_PER_GROUP} first orders, worst repeat rate first")
print(category.round(4).to_string(index=False))

state = compare(first, "customer_state", "F. Customer states")
state = state[state["orders"] >= MIN_ORDERS_PER_GROUP].sort_values("late_rate", ascending=False)
title("F2. States ranked by late delivery rate (where to fix logistics first)")
print(state.round(4).to_string(index=False))

for name, df in [("rc_late_vs_ontime", late), ("rc_delay_buckets", delay), ("rc_review_scores", review),
                 ("rc_freight", freight), ("rc_categories", category), ("rc_states", state)]:
    save_csv(df, name)
save_csv(first, "first_orders")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].bar(delay["delay_bucket"].astype(str), delay["avg_review"], color="#4C78A8")
axes[0].set_title("Average review score by delivery delay")
axes[0].set_ylim(1, 5)
axes[0].tick_params(axis="x", rotation=30)
axes[1].bar(review["review"].astype(str), review["repeat_rate"], color="#F58518")
axes[1].set_title("Repeat purchase rate by first-order review score")
axes[1].set_xlabel("Review score")
axes[1].yaxis.set_major_formatter(PercentFormatter(1.0))
save_chart(fig, "root_cause")
