"""Step 7: Put a money value on the problem and write the executive summary.

Two numbers a manager cares about:
  1. Revenue at risk  : how much our high-value-but-quiet customers have been worth
  2. Recoverable revenue : what fixing late deliveries could bring back
"""
import pandas as pd

from common import OUTPUTS, load_processed, save_csv, title

rfm = pd.read_csv(OUTPUTS / "rfm_customers.csv")
first = pd.read_csv(OUTPUTS / "first_orders.csv", parse_dates=["purchase_ts"])
orders = load_processed("orders_fact")
delivered = orders[orders["order_status"] == "delivered"]

# --- 1. Revenue at risk -------------------------------------------------------
at_risk = rfm[rfm["segment"] == "At Risk"]
at_risk_customers = len(at_risk)
at_risk_revenue = at_risk["monetary"].sum()
at_risk_share = at_risk_revenue / rfm["monetary"].sum()

# --- 2. Recoverable revenue from fixing late deliveries -------------------------
repeat_on_time = first.loc[first["is_late"] == 0, "has_repeat"].mean()
repeat_late = first.loc[first["is_late"] == 1, "has_repeat"].mean()
late_first_orders = int((first["is_late"] == 1).sum())

# Value of a customer who comes back = what they spend on orders 2, 3, ...
later_orders = delivered[delivered["delivered_order_number"] > 1]
value_per_returning_customer = (
    later_orders.groupby("customer_unique_id")["order_revenue"].sum().mean()
)

extra_returning_customers = late_first_orders * max(repeat_on_time - repeat_late, 0)
months_observed = max(
    (first["purchase_ts"].max() - first["purchase_ts"].min()).days / 30.44, 1
)
recoverable_full_fix = extra_returning_customers * value_per_returning_customer
recoverable_per_year = recoverable_full_fix * 12 / months_observed
recoverable_half_fix = recoverable_per_year / 2

late_reviews = first.groupby("is_late")["review_score"].mean()

numbers = {
    "at_risk_customers": at_risk_customers,
    "at_risk_historical_revenue": at_risk_revenue,
    "at_risk_share_of_revenue": at_risk_share,
    "late_first_orders": late_first_orders,
    "late_rate_first_orders": first["is_late"].mean(),
    "avg_review_on_time": late_reviews.get(0),
    "avg_review_late": late_reviews.get(1),
    "repeat_rate_on_time": repeat_on_time,
    "repeat_rate_late": repeat_late,
    "value_per_returning_customer": value_per_returning_customer,
    "extra_returning_customers_if_no_late": extra_returning_customers,
    "recoverable_revenue_per_year_full_fix": recoverable_per_year,
    "recoverable_revenue_per_year_half_fix": recoverable_half_fix,
}

title("Key numbers")
for k, v in numbers.items():
    print(f"{k:42s} {v:,.4f}")
save_csv(pd.DataFrame(list(numbers.items()), columns=["metric", "value"]), "key_numbers")

worst_states = pd.read_csv(OUTPUTS / "rc_states.csv").head(3)["customer_state"].tolist()
relative_drop = 1 - repeat_late / repeat_on_time if repeat_on_time else 0

memo = f"""EXECUTIVE SUMMARY - Revenue at Risk from Poor First-Order Experience

PROBLEM
Most customers buy once and never return. We analysed {len(first):,} first orders to find out why.

KEY FINDINGS
1. {first['is_late'].mean():.1%} of first orders arrived after the promised date.
2. Late orders average a {late_reviews.get(1, float('nan')):.2f}-star review vs {late_reviews.get(0, float('nan')):.2f} for on-time orders.
3. Customers whose first order was late come back {relative_drop:.0%} less often
   ({repeat_late:.2%} vs {repeat_on_time:.2%} repeat rate).
4. {at_risk_customers:,} high-value customers have gone quiet ("At Risk" segment). They account for
   R${at_risk_revenue:,.0f} ({at_risk_share:.1%}) of historical revenue.
5. Late deliveries are most common in: {', '.join(worst_states)}.

OPPORTUNITY
- Eliminating late first deliveries is worth about R${recoverable_per_year:,.0f} per year in repeat revenue.
- Cutting them by half is worth about R${recoverable_half_fix:,.0f} per year.

RECOMMENDATIONS
1. Logistics: add delivery-time buffers / better carriers for {', '.join(worst_states)}.
2. Service recovery: when an order is late, automatically send an apology + voucher before the
   customer leaves a review.
3. Win-back: target the {at_risk_customers:,} At Risk customers with a personalised campaign.
4. Track monthly: late delivery rate, first-order review score, 90-day repeat rate.

CAVEAT
This is correlation, not proof of causation. An A/B test of the voucher in recommendation 2
would confirm the effect before scaling.
"""
(OUTPUTS / "executive_summary.txt").write_text(memo)
title("Executive summary (saved to outputs/executive_summary.txt)")
print(memo)
