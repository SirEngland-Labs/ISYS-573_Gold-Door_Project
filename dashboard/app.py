"""Streamlit admin dashboard — view and manage restaurant reservations."""

import os
import sys
from datetime import date, datetime, timedelta

import streamlit as st

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import (
    init_db,
    get_reservations_by_date,
    get_all_tables,
    check_availability,
    cancel_reservation,
)
from dashboard.auth import check_password

# Page config
st.set_page_config(
    page_title="Restaurant Admin",
    page_icon="🍽️",
    layout="wide",
)

# Initialize database
init_db()

# Auth gate
if not check_password():
    st.stop()

# --- Sidebar ---
st.sidebar.title("🍽️ Restaurant Admin")
page = st.sidebar.radio("Navigate", ["Reservations", "Availability", "Tables"])

# --- Reservations Page ---
if page == "Reservations":
    st.title("📋 Reservations")

    # Date picker — default to today
    selected_date = st.date_input("Select date", value=date.today())

    reservations = get_reservations_by_date(selected_date)

    if not reservations:
        st.info(f"No reservations for {selected_date.strftime('%A, %B %d, %Y')}.")
    else:
        st.success(f"{len(reservations)} reservation(s) for {selected_date.strftime('%A, %B %d, %Y')}")

        for res in reservations:
            with st.expander(
                f"⏰ {res['time']} — {res['customer_name']} ({res['party_size']} guests)"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Confirmation #:** {res['id']}")
                    st.write(f"**Name:** {res['customer_name']}")
                    st.write(f"**Phone:** {res['customer_phone']}")
                    st.write(f"**Party size:** {res['party_size']}")

                with col2:
                    st.write(f"**Date:** {res['date']}")
                    st.write(f"**Time:** {res['time']}")
                    st.write(f"**Table:** {res.get('table_name', 'N/A')} ({res.get('table_location', 'N/A')})")
                    st.write(f"**Status:** {res['status']}")

                if res.get('special_requests'):
                    st.write(f"**Special requests:** {res['special_requests']}")

                # Cancel button
                if st.button(f"Cancel Reservation #{res['id']}", key=f"cancel_{res['id']}"):
                    try:
                        cancel_reservation(reservation_id=res['id'])
                        st.warning(f"Reservation #{res['id']} cancelled.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- Availability Page ---
elif page == "Availability":
    st.title("📊 Availability")

    col1, col2 = st.columns(2)
    with col1:
        check_date = st.date_input("Date", value=date.today(), key="avail_date")
    with col2:
        party_size = st.number_input("Party size", min_value=1, max_value=10, value=2)

    if st.button("Check Availability"):
        from datetime import time as dt_time

        st.subheader(f"Available tables for {party_size} guests on {check_date}")

        # Check common time slots
        time_slots = [
            dt_time(11, 30), dt_time(12, 0), dt_time(12, 30),
            dt_time(13, 0), dt_time(17, 0), dt_time(17, 30),
            dt_time(18, 0), dt_time(18, 30), dt_time(19, 0),
            dt_time(19, 30), dt_time(20, 0), dt_time(20, 30),
            dt_time(21, 0),
        ]

        for slot in time_slots:
            available = check_availability(check_date, slot, party_size)
            slot_str = slot.strftime("%I:%M %p")

            if available:
                table_names = ", ".join([t['name'] for t in available])
                st.write(f"✅ **{slot_str}** — {len(available)} table(s): {table_names}")
            else:
                st.write(f"❌ **{slot_str}** — Fully booked")

# --- Tables Page ---
elif page == "Tables":
    st.title("🪑 Restaurant Tables")

    tables = get_all_tables()

    if not tables:
        st.warning("No tables configured.")
    else:
        # Summary
        total_capacity = sum(t['capacity'] for t in tables)
        indoor = [t for t in tables if t['location'] == 'indoor']
        outdoor = [t for t in tables if t['location'] == 'outdoor']

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Tables", len(tables))
        col2.metric("Total Capacity", f"{total_capacity} seats")
        col3.metric("Indoor / Outdoor", f"{len(indoor)} / {len(outdoor)}")

        st.divider()

        # Table list
        for t in tables:
            icon = "🏠" if t['location'] == 'indoor' else "🌿"
            st.write(f"{icon} **{t['name']}** — {t['capacity']} seats ({t['location']})")
