"""Step 2: Run sql/build_model.sql with DuckDB and export clean tables.

DuckDB is a free SQL engine that runs inside Python, so you don't need to install
a database server. The SQL is standard and also runs on PostgreSQL.
"""
import duckdb

from common import PROCESSED, ROOT, RAW_FILES, load_raw, save_csv, title

con = duckdb.connect()
for name in RAW_FILES:
    con.register(name, load_raw(name))

con.execute((ROOT / "sql" / "build_model.sql").read_text())

title("Sanity checks")
n_orders_raw = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
n_orders_fact = con.execute("SELECT COUNT(*) FROM orders_fact").fetchone()[0]
print(f"Raw orders: {n_orders_raw:,}  |  orders_fact rows: {n_orders_fact:,}")
assert n_orders_raw == n_orders_fact, "Join changed the row count: check for duplicate keys"

raw_revenue, fact_revenue = con.execute("""
    SELECT (SELECT SUM(price + freight_value) FROM items),
           (SELECT SUM(order_revenue) FROM orders_fact)
""").fetchone()
print(f"Revenue in items table: {raw_revenue:,.2f}  |  in orders_fact: {fact_revenue:,.2f}")
assert abs(raw_revenue - fact_revenue) < 1, "Revenue doesn't reconcile: rows were duplicated or lost"

print(con.execute("""
    SELECT COUNT(*) AS delivered_customers,
           SUM(CASE WHEN n_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers
    FROM customer_summary
""").df().to_string(index=False))

title("Saving clean tables")
save_csv(con.table("orders_fact").df(), "orders_fact", folder=PROCESSED)
save_csv(con.table("customer_summary").df(), "customer_summary", folder=PROCESSED)
