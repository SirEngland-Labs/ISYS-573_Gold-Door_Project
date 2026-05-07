"""Tool wrappers for checking table availability."""

from datetime import date, time
from typing import Optional
from app.database import check_availability, get_all_tables


def check_table_availability(query_date: str, query_time: Optional[str] = None, party_size: int = 2) -> str:
    """Check available tables for a given date/time/party size.

    Args:
        query_date: Date string in YYYY-MM-DD format
        query_time: Optional time string in HH:MM format
        party_size: Number of guests

    Returns:
        Formatted string describing availability.
    """
    try:
        d = date.fromisoformat(query_date)
        t = time.fromisoformat(query_time) if query_time else None

        available = check_availability(d, t, party_size)

        if not available:
            return f"Sorry, no tables available for {party_size} guests on {query_date}" + (f" at {query_time}" if query_time else "") + ". Try a different date or time."

        table_list = ", ".join([f"{t['name']} ({t['location']}, seats {t['capacity']})" for t in available])
        return f"{len(available)} table(s) available for {party_size} guests on {query_date}" + (f" at {query_time}" if query_time else "") + f": {table_list}"
    except Exception as e:
        return f"Error checking availability: {str(e)}"


def list_all_tables() -> str:
    """List all restaurant tables with capacity info."""
    tables = get_all_tables()
    lines = [f"- {t['name']}: {t['capacity']} seats ({t['location']})" for t in tables]
    return "Restaurant tables:\n" + "\n".join(lines)
