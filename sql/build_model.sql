-- Step 2: Build a clean analytical model from the 8 raw tables.
--
-- Output tables and their grain (what one row means):
--   orders_fact       one row per order
--   customer_summary  one row per real customer (customer_unique_id), delivered orders only
--
-- Rule of thumb: aggregate every "many" table (items, reviews, payments) to one row
-- per order BEFORE joining, otherwise the join multiplies rows and inflates revenue.

-- Items: one order can contain several items.
CREATE OR REPLACE TABLE order_items_agg AS
SELECT
    order_id,
    COUNT(*)           AS n_items,
    SUM(price)         AS product_value,
    SUM(freight_value) AS freight_value
FROM items
GROUP BY order_id;

-- Main category of an order = category of its most expensive item.
CREATE OR REPLACE TABLE order_category AS
SELECT order_id, category
FROM (
    SELECT
        i.order_id,
        COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
        ROW_NUMBER() OVER (PARTITION BY i.order_id ORDER BY i.price DESC, i.order_item_id) AS rn
    FROM items i
    LEFT JOIN products p ON p.product_id = i.product_id
    LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
) ranked
WHERE rn = 1;

-- Reviews: a few orders have more than one review, so average them.
CREATE OR REPLACE TABLE order_review AS
SELECT order_id, AVG(review_score) AS review_score
FROM reviews
GROUP BY order_id;

-- Payments: an order can be paid with several methods (e.g. voucher + card).
CREATE OR REPLACE TABLE order_payment AS
SELECT
    order_id,
    SUM(payment_value)        AS payment_value,
    MAX(payment_installments) AS installments
FROM payments
GROUP BY order_id;

CREATE OR REPLACE TABLE orders_fact AS
WITH base AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        o.order_status,
        CAST(o.order_purchase_timestamp AS TIMESTAMP)      AS purchase_ts,
        CAST(o.order_delivered_customer_date AS TIMESTAMP) AS delivered_ts,
        CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS estimated_ts
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
)
SELECT
    b.order_id,
    b.customer_unique_id,
    b.customer_state,
    b.order_status,
    b.purchase_ts,
    b.delivered_ts,
    b.estimated_ts,
    DATE_TRUNC('month', b.purchase_ts)                          AS purchase_month,
    CAST(b.delivered_ts AS DATE) - CAST(b.purchase_ts AS DATE)  AS delivery_days,
    -- positive = arrived after the promised date, negative = arrived early
    CAST(b.delivered_ts AS DATE) - CAST(b.estimated_ts AS DATE) AS days_vs_estimate,
    CASE
        WHEN b.delivered_ts IS NULL THEN NULL
        WHEN CAST(b.delivered_ts AS DATE) > CAST(b.estimated_ts AS DATE) THEN 1
        ELSE 0
    END AS is_late,
    ia.n_items,
    ia.product_value,
    ia.freight_value,
    ia.product_value + ia.freight_value                              AS order_revenue,
    ia.freight_value / NULLIF(ia.product_value + ia.freight_value, 0) AS freight_share,
    oc.category,
    r.review_score,
    p.payment_value,
    p.installments,
    -- 1 = the customer's first delivered order, 2 = second, ...
    CASE WHEN b.order_status = 'delivered' THEN
        ROW_NUMBER() OVER (
            PARTITION BY b.customer_unique_id, b.order_status = 'delivered'
            ORDER BY b.purchase_ts
        )
    END AS delivered_order_number
FROM base b
LEFT JOIN order_items_agg ia ON ia.order_id = b.order_id
LEFT JOIN order_category  oc ON oc.order_id = b.order_id
LEFT JOIN order_review    r  ON r.order_id  = b.order_id
LEFT JOIN order_payment   p  ON p.order_id  = b.order_id;

CREATE OR REPLACE TABLE customer_summary AS
SELECT
    customer_unique_id,
    MIN(customer_state) AS customer_state,
    MIN(purchase_ts)    AS first_purchase_ts,
    MAX(purchase_ts)    AS last_purchase_ts,
    COUNT(*)            AS n_orders,
    SUM(order_revenue)  AS total_revenue,
    AVG(review_score)   AS avg_review_score
FROM orders_fact
WHERE order_status = 'delivered'
GROUP BY customer_unique_id;
