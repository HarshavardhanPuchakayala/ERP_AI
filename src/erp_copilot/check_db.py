
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "erp.db"
conn = sqlite3.connect(DB_PATH)


def show(title, sql):
    print(f"\n=== {title} ===")
    for row in conn.execute(sql):
        print(row)


show("Row counts", """
    SELECT 'customers', COUNT(*) FROM customers UNION ALL
    SELECT 'products', COUNT(*) FROM products UNION ALL
    SELECT 'orders', COUNT(*) FROM sales_orders UNION ALL
    SELECT 'invoices', COUNT(*) FROM sales_invoices
""")

show("Q1: details of Grant Plastics Ltd.",
     "SELECT * FROM customers WHERE name = 'Grant Plastics Ltd.'")

show("Q2: invoices in the last 30 days (count)",
     "SELECT COUNT(*) FROM sales_invoices WHERE invoice_date >= date('now', '-30 days')")

show("Q3: top 5 customers by total invoiced", """
    SELECT c.name, ROUND(SUM(i.grand_total), 2) AS total
    FROM sales_invoices i JOIN customers c ON c.id = i.customer_id
    GROUP BY c.id ORDER BY total DESC LIMIT 5
""")

show("Q4: customers who still owe money", """
    SELECT c.name, ROUND(SUM(i.grand_total - i.amount_paid), 2) AS owed
    FROM sales_invoices i JOIN customers c ON c.id = i.customer_id
    GROUP BY c.id HAVING owed > 0 ORDER BY owed DESC
""")

conn.close()