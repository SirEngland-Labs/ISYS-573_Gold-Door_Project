"""Tool wrappers for creating and cancelling reservations."""

from datetime import date, time
from typing import Optional
from app.database import create_reservation, cancel_reservation, get_reservations_by_phone


def make_reservation(customer_name: str, customer_phone: str, party_size: int,
                     res_date: str, res_time: str, special_requests: Optional[str] = None) -> str:
    """Create a reservation.

    Args:
        customer_name: Guest name
        customer_phone: Phone number
        party_size: Number of guests
        res_date: Date in YYYY-MM-DD format
        res_time: Time in HH:MM format
        special_requests: Optional dietary/occasion notes

    Returns:
        Confirmation message or error.
    """
    try:
        d = date.fromisoformat(res_date)
        t = time.fromisoformat(res_time)

        result = create_reservation(
            customer_name=customer_name,
            customer_phone=customer_phone,
            party_size=party_size,
            res_date=d,
            res_time=t,
            special_requests=special_requests
        )

        return (
            f"Reservation confirmed!\n"
            f"- Confirmation #: {result['id']}\n"
            f"- Name: {result['customer_name']}\n"
            f"- Party size: {result['party_size']}\n"
            f"- Date: {result['date']}\n"
            f"- Time: {result['time']}\n"
            f"- Table: {result['table']} ({result['table_location']})\n"
            + (f"- Special requests: {result['special_requests']}\n" if result['special_requests'] else "")
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error creating reservation: {str(e)}"


def cancel_booking(reservation_id: Optional[int] = None, customer_phone: Optional[str] = None) -> str:
    """Cancel a reservation by ID or phone number.

    Returns confirmation or error message.
    """
    try:
        result = cancel_reservation(reservation_id=reservation_id, customer_phone=customer_phone)
        return f"Reservation #{result['id']} for {result['customer_name']} on {result['date']} at {result['time']} has been cancelled."
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error cancelling reservation: {str(e)}"


def lookup_reservations(customer_phone: str) -> str:
    """Look up upcoming reservations for a phone number."""
    try:
        reservations = get_reservations_by_phone(customer_phone)
        if not reservations:
            return "No upcoming reservations found for this phone number."

        lines = []
        for r in reservations:
            lines.append(
                f"- #{r['id']}: {r['customer_name']}, {r['party_size']} guests, "
                f"{r['date']} at {r['time']}, {r.get('table_name', 'TBD')}"
            )
        return "Upcoming reservations:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error looking up reservations: {str(e)}"
