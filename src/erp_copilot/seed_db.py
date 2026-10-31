"""Creates data/erp.db with fake ERP-style sales data."""
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "erp.db"
SCHEMA = """
DROP TABLE IF EXISTS sales_invoices;
DROP TABLE IF EXISTS sales_order_items;
DROP TABLE IF EXISTS sales_orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    city TEXT,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    unit_price REAL NOT NULL
);

CREATE TABLE sales_orders (
    id INTEGER PRIMARY KEY,
    order_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE sales_order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES sales_orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE sales_invoices (
    id INTEGER PRIMARY KEY,
    invoice_no TEXT NOT NULL UNIQUE,
    order_id INTEGER NOT NULL REFERENCES sales_orders(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    grand_total REAL NOT NULL,
    amount_paid REAL NOT NULL DEFAULT 0
);
"""

CUSTOMERS = [
    ("Grant Plastics Ltd.", "Mumbai"),
    ("Palmer Steel Works", "Pune"),
    ("Sunrise Traders", "Delhi"),
    ("Blue Lotus Exports", "Chennai"),
    ("Kumar & Sons Hardware", "Hyderabad"),
    ("Eastern Packaging Co.", "Kolkata"),
    ("Vega Electronics", "Bengaluru"),
    ("Orchid Textiles", "Surat"),
    ("Metro Office Supplies", "Ahmedabad"),
    ("Northstar Logistics", "Jaipur"),
    ("Greenfield Agro", "Nagpur"),
    ("Silverline Furniture", "Lucknow"),
    ("Apex Auto Parts", "Chandigarh"),
    ("Harbor Foods Pvt Ltd", "Kochi"),
    ("Zenith Chemicals", "Vadodara"),
]

PRODUCTS = [
    ("Steel Rod 12mm", 450.0),
    ("Plastic Granules 25kg", 1800.0),
    ("Cotton Fabric Roll", 3200.0),
    ("Cardboard Box (100 pcs)", 950.0),
    ("LED Panel Light", 700.0),
    ("Office Chair", 4200.0),
    ("Copper Wire 50m", 2600.0),
    ("Industrial Paint 20L", 3900.0),
    ("Safety Gloves (dozen)", 520.0),
    ("Packing Tape (carton)", 1100.0),
]

NUM_ORDERS = 70


def build_database() -> None:
    random.seed(42)  # same data every time you run this
    today = date.today()

    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    for i, (name, city) in enumerate(CUSTOMERS, start=1):
        email = name.lower().replace(" ", "").replace(".", "").replace("&", "and")[:20] + "@example.com"
        created = (today - timedelta(days=random.randint(200, 700))).isoformat()
        conn.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?, ?)", (i, name, city, email, created)
        )

    for i, (name, price) in enumerate(PRODUCTS, start=1):
        conn.execute("INSERT INTO products VALUES (?, ?, ?)", (i, name, price))

    # Orders in the last ~120 days, sorted so numbers rise with date
    order_dates = sorted(today - timedelta(days=random.randint(0, 120)) for _ in range(NUM_ORDERS))

    item_id = 1
    for n, order_date in enumerate(order_dates, start=1):
        customer_id = random.randint(1, len(CUSTOMERS))
        days_old = (today - order_date).days
        status = "Open" if days_old < 7 else "Completed"
        conn.execute(
            "INSERT INTO sales_orders VALUES (?, ?, ?, ?, ?)",
            (n, f"SO-{n:04d}", customer_id, order_date.isoformat(), status),
        )

        total = 0.0
        for product_id in random.sample(range(1, len(PRODUCTS) + 1), random.randint(1, 4)):
            qty = random.randint(1, 20)
            price = PRODUCTS[product_id - 1][1]
            total += qty * price
            conn.execute(
                "INSERT INTO sales_order_items VALUES (?, ?, ?, ?, ?)",
                (item_id, n, product_id, qty, price),
            )
            item_id += 1

        invoice_date = min(order_date + timedelta(days=1), today)
        due_date = invoice_date + timedelta(days=30)

        roll = random.random()
        if roll < 0.6:
            paid = total                                  # fully paid
        elif roll < 0.8:
            paid = round(total * random.uniform(0.3, 0.7), 2)  # partly paid
        else:
            paid = 0.0                                    # unpaid

        conn.execute(
            "INSERT INTO sales_invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (n, f"SINV-{n:04d}", n, customer_id,
             invoice_date.isoformat(), due_date.isoformat(), round(total, 2), paid),
        )

    conn.commit()
    conn.close()
    print(f"Database created at: {DB_PATH}")


if __name__ == "__main__":
    build_database()