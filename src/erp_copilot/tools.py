import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "erp.db"
MAX_ROWS = 50


def _connect() -> sqlite3.Connection:
    # mode=ro opens the database read-only: any write attempt fails
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _limit(n) -> int:
    return max(1, min(int(n), MAX_ROWS))


def _check_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")


def find_customer(name: str, limit: int = 5) -> list[dict]:
    """Find customers whose name contains the given text, with totals."""
    return _query(
        """
        SELECT c.id, c.name, c.city, c.email, c.created_at,
               ROUND(COALESCE(SUM(i.grand_total), 0), 2) AS total_invoiced,
               ROUND(COALESCE(SUM(i.grand_total - i.amount_paid), 0), 2) AS outstanding
        FROM customers c
        LEFT JOIN sales_invoices i ON i.customer_id = c.id
        WHERE c.name LIKE ?
        GROUP BY c.id
        LIMIT ?
        """,
        (f"%{name}%", _limit(limit)),
    )


def list_invoices(start_date: str, end_date: str, limit: int = 20) -> list[dict]:
    """List invoices dated between start_date and end_date (YYYY-MM-DD)."""
    return _query(
        """
        SELECT i.invoice_no, c.name AS customer, i.invoice_date, i.due_date,
               i.grand_total, i.amount_paid,
               ROUND(i.grand_total - i.amount_paid, 2) AS outstanding
        FROM sales_invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.invoice_date BETWEEN ? AND ?
        ORDER BY i.invoice_date DESC
        LIMIT ?
        """,
        (_check_date(start_date), _check_date(end_date), _limit(limit)),
    )


def top_customers(limit: int = 5, start_date: str | None = None,
                  end_date: str | None = None) -> list[dict]:
    """Rank customers by total invoiced, optionally within a date range."""
    start = _check_date(start_date) if start_date else None
    end = _check_date(end_date) if end_date else None
    return _query(
        """
        SELECT c.name, ROUND(SUM(i.grand_total), 2) AS total_invoiced,
               COUNT(i.id) AS invoice_count
        FROM sales_invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE (? IS NULL OR i.invoice_date >= ?)
          AND (? IS NULL OR i.invoice_date <= ?)
        GROUP BY c.id
        ORDER BY total_invoiced DESC
        LIMIT ?
        """,
        (start, start, end, end, _limit(limit)),
    )


def customers_who_owe(limit: int = 20) -> list[dict]:
    """List customers with unpaid balances, largest first."""
    return _query(
        """
        SELECT c.name, ROUND(SUM(i.grand_total - i.amount_paid), 2) AS amount_owed,
               COUNT(*) AS unpaid_invoices
        FROM sales_invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.grand_total - i.amount_paid > 0
        GROUP BY c.id
        ORDER BY amount_owed DESC
        LIMIT ?
        """,
        (_limit(limit),),
    )


def get_invoice(invoice_no: str) -> list[dict]:
    """Get one invoice by its number, for example SINV-0005."""
    return _query(
        """
        SELECT i.invoice_no, c.name AS customer, i.invoice_date, i.due_date,
               i.grand_total, i.amount_paid,
               ROUND(i.grand_total - i.amount_paid, 2) AS outstanding
        FROM sales_invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.invoice_no = ?
        """,
        (invoice_no.strip().upper(),),
    )


# The "menu" the agent will be allowed to use (wired up in Part 3C)
TOOL_FUNCTIONS = {
    "find_customer": find_customer,
    "list_invoices": list_invoices,
    "top_customers": top_customers,
    "customers_who_owe": customers_who_owe,
    "get_invoice": get_invoice,
}