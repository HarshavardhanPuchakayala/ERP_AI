
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from knowledge import search_documents
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


def get_date_range(period: str) -> dict:
    """Get the exact start_date and end_date (YYYY-MM-DD) for a named period.
    Use this BEFORE any date-based question. period must be one of: today,
    yesterday, this_week, last_week, this_month, last_month, last_30_days,
    this_quarter, last_quarter, this_year, last_year."""
    today = date.today()
    p = period.strip().lower().replace(" ", "_")

    if p == "today":
        start, end = today, today
    elif p == "yesterday":
        start = end = today - timedelta(days=1)
    elif p == "this_week":
        start, end = today - timedelta(days=today.weekday()), today
    elif p == "last_week":
        this_monday = today - timedelta(days=today.weekday())
        start, end = this_monday - timedelta(days=7), this_monday - timedelta(days=1)
    elif p == "this_month":
        start, end = today.replace(day=1), today
    elif p == "last_month":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    elif p == "last_30_days":
        start, end = today - timedelta(days=30), today
    elif p in ("this_quarter", "last_quarter"):
        this_q_start = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        if p == "this_quarter":
            start, end = this_q_start, today
        else:
            end = this_q_start - timedelta(days=1)
            start = date(end.year, 3 * ((end.month - 1) // 3) + 1, 1)
    elif p == "this_year":
        start, end = date(today.year, 1, 1), today
    elif p == "last_year":
        start, end = date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    else:
        raise ValueError(f"Unknown period '{period}'.")

    return {"period": p, "start_date": start.isoformat(), "end_date": end.isoformat()}


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


def list_invoices(start_date: str, end_date: str, limit: int = 20) -> dict:
    """List invoices dated between start_date and end_date (YYYY-MM-DD).
    Returns pre-computed totals for ALL matching invoices, plus up to
    'limit' invoice rows."""
    start, end = _check_date(start_date), _check_date(end_date)
    totals = _query(
        """
        SELECT COUNT(*) AS invoice_count,
               ROUND(COALESCE(SUM(grand_total), 0), 2) AS total_invoiced,
               ROUND(COALESCE(SUM(amount_paid), 0), 2) AS total_paid,
               ROUND(COALESCE(SUM(grand_total - amount_paid), 0), 2) AS total_outstanding
        FROM sales_invoices
        WHERE invoice_date BETWEEN ? AND ?
        """,
        (start, end),
    )[0]
    rows = _query(
        """
        SELECT i.invoice_no, c.name AS customer, i.invoice_date, i.due_date,
               i.grand_total, i.amount_paid,
               ROUND(i.grand_total - i.amount_paid, 2) AS outstanding
        FROM sales_invoices i
        JOIN customers c ON c.id = i.customer_id
        WHERE i.invoice_date BETWEEN ? AND ?
        ORDER BY i.invoice_date DESC, i.invoice_no DESC
        LIMIT ?
        """,
        (start, end, _limit(limit)),
    )
    return {
        "start_date": start,
        "end_date": end,
        **totals,
        "rows_returned": len(rows),
        "truncated": totals["invoice_count"] > len(rows),
        "invoices": rows,
    }


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


def customers_who_owe(limit: int = 20) -> dict:
    """List customers with unpaid balances, largest first. Returns
    pre-computed totals across ALL customers who owe money."""
    totals = _query(
        """
        SELECT COUNT(DISTINCT customer_id) AS customer_count,
               COUNT(*) AS unpaid_invoice_count,
               ROUND(COALESCE(SUM(grand_total - amount_paid), 0), 2) AS total_owed
        FROM sales_invoices
        WHERE grand_total - amount_paid > 0
        """
    )[0]
    rows = _query(
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
    return {
        **totals,
        "rows_returned": len(rows),
        "truncated": totals["customer_count"] > len(rows),
        "customers": rows,
    }


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


# The "menu" the agent is allowed to use. Nothing outside this dict can run.
TOOL_FUNCTIONS = {
    "get_date_range": get_date_range,
    "find_customer": find_customer,
    "list_invoices": list_invoices,
    "top_customers": top_customers,
    "customers_who_owe": customers_who_owe,
    "get_invoice": get_invoice,
    "search_documents": search_documents,
}