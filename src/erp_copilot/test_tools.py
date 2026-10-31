
import json
from datetime import date, timedelta

import tools


def show(title, rows):
    print(f"\n=== {title} ===")
    print(json.dumps(rows, indent=2))


today = date.today()
month_ago = today - timedelta(days=30)

show("find_customer('Grant')", tools.find_customer("Grant"))
show("list_invoices (last 30 days, 3 rows)",
     tools.list_invoices(month_ago.isoformat(), today.isoformat(), limit=3))
show("top_customers(3)", tools.top_customers(limit=3))
show("customers_who_owe(3)", tools.customers_who_owe(limit=3))
show("get_invoice('sinv-0005')", tools.get_invoice("sinv-0005"))
show("get_invoice('SINV-9999') -> should be empty", tools.get_invoice("SINV-9999"))

print("\n=== SAFETY CHECK: try to delete an invoice ===")
try:
    conn = tools._connect()
    conn.execute("DELETE FROM sales_invoices WHERE invoice_no = 'SINV-0001'")
    print("DANGER: the delete worked!")
except Exception as e:
    print("Blocked as expected ->", type(e).__name__, ":", e)