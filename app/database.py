"""SQLite database setup and connection management."""

import sqlite3
import os
from datetime import date, time, datetime, timedelta
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "data/reservations.db")


def get_connection():
    """Get SQLite connection. Creates data directory if needed."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed default restaurant tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create tables table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            location TEXT NOT NULL DEFAULT 'indoor'
        )
    """)

    # Create reservations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            party_size INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            table_id INTEGER,
            status TEXT NOT NULL DEFAULT 'confirmed',
            special_requests TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (table_id) REFERENCES tables(id)
        )
    """)

    # Seed tables if empty
    cursor.execute("SELECT COUNT(*) FROM tables")
    if cursor.fetchone()[0] == 0:
        default_tables = [
            ("Table 1", 2, "indoor"),
            ("Table 2", 2, "indoor"),
            ("Table 3", 4, "indoor"),
            ("Table 4", 4, "indoor"),
            ("Table 5", 6, "indoor"),
            ("Table 6", 6, "indoor"),
            ("Table 7", 8, "outdoor"),
            ("Table 8", 4, "outdoor"),
            ("Table 9", 2, "outdoor"),
            ("Table 10", 10, "indoor"),
        ]
        cursor.executemany(
            "INSERT INTO tables (name, capacity, location) VALUES (?, ?, ?)",
            default_tables
        )

    conn.commit()
    conn.close()


def check_availability(query_date: date, query_time: Optional[time], party_size: int) -> list[dict]:
    """Check which tables are available for given date/time/party size.

    A table is available if:
    - It can seat the party (capacity >= party_size)
    - No confirmed reservation exists for that table within a 2-hour window of the requested time

    Returns list of available tables.
    """
    conn = get_connection()
    cursor = conn.cursor()

    date_str = query_date.isoformat()

    # Get all tables that can fit the party
    cursor.execute("SELECT * FROM tables WHERE capacity >= ?", (party_size,))
    suitable_tables = [dict(row) for row in cursor.fetchall()]

    if not query_time:
        # No specific time — return all suitable tables
        conn.close()
        return suitable_tables

    # Check which suitable tables are booked at this time (2-hour window)
    time_str = query_time.isoformat()
    booked_table_ids = set()

    cursor.execute("""
        SELECT table_id FROM reservations
        WHERE date = ? AND status = 'confirmed' AND table_id IS NOT NULL
    """, (date_str,))

    for row in cursor.fetchall():
        # For simplicity, check all confirmed reservations on that date
        # A more precise check would compare time windows
        cursor.execute("""
            SELECT time FROM reservations
            WHERE date = ? AND table_id = ? AND status = 'confirmed'
        """, (date_str, row["table_id"]))
        for res_row in cursor.fetchall():
            res_time = time.fromisoformat(res_row["time"])
            req_minutes = query_time.hour * 60 + query_time.minute
            res_minutes = res_time.hour * 60 + res_time.minute
            if abs(req_minutes - res_minutes) < 120:  # 2-hour window
                booked_table_ids.add(row["table_id"])

    available = [t for t in suitable_tables if t["id"] not in booked_table_ids]
    conn.close()
    return available


def create_reservation(customer_name: str, customer_phone: str, party_size: int,
                       res_date: date, res_time: time,
                       special_requests: Optional[str] = None) -> dict:
    """Create a new reservation. Auto-assigns a table.

    Returns the reservation dict, or raises ValueError if no tables available.
    """
    available = check_availability(res_date, res_time, party_size)
    if not available:
        raise ValueError("No tables available for the requested date, time, and party size.")

    # Pick the smallest suitable table (best fit)
    table = min(available, key=lambda t: t["capacity"])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reservations (customer_name, customer_phone, party_size, date, time, table_id, special_requests)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (customer_name, customer_phone, party_size, res_date.isoformat(), res_time.isoformat(), table["id"], special_requests))

    reservation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": reservation_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "party_size": party_size,
        "date": res_date.isoformat(),
        "time": res_time.isoformat(),
        "table": table["name"],
        "table_location": table["location"],
        "special_requests": special_requests,
        "status": "confirmed"
    }


def cancel_reservation(reservation_id: Optional[int] = None,
                        customer_phone: Optional[str] = None) -> dict:
    """Cancel a reservation by ID or phone number.

    If phone number is given, cancels the most recent upcoming confirmed reservation for that phone.
    Returns the cancelled reservation dict, or raises ValueError if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if reservation_id:
        cursor.execute("SELECT * FROM reservations WHERE id = ? AND status = 'confirmed'", (reservation_id,))
    elif customer_phone:
        cursor.execute("""
            SELECT * FROM reservations
            WHERE customer_phone = ? AND status = 'confirmed' AND date >= ?
            ORDER BY date ASC, time ASC LIMIT 1
        """, (customer_phone, date.today().isoformat()))
    else:
        raise ValueError("Provide either reservation_id or customer_phone.")

    row = cursor.fetchone()
    if not row:
        raise ValueError("No confirmed reservation found.")

    res = dict(row)
    cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (res["id"],))
    conn.commit()
    conn.close()

    res["status"] = "cancelled"
    return res


def get_reservations_by_date(query_date: date) -> list[dict]:
    """Get all confirmed reservations for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, t.name as table_name, t.location as table_location
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        WHERE r.date = ? AND r.status = 'confirmed'
        ORDER BY r.time ASC
    """, (query_date.isoformat(),))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_reservations_by_phone(phone: str) -> list[dict]:
    """Get all reservations for a phone number (upcoming, confirmed)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, t.name as table_name, t.location as table_location
        FROM reservations r
        LEFT JOIN tables t ON r.table_id = t.id
        WHERE r.customer_phone = ? AND r.status = 'confirmed' AND r.date >= ?
        ORDER BY r.date ASC, r.time ASC
    """, (phone, date.today().isoformat()))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_tables() -> list[dict]:
    """Get all restaurant tables."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tables ORDER BY id")
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results
