"""Simple password authentication for the admin dashboard."""

import os
import hashlib
import streamlit as st


def check_password() -> bool:
    """Show a login form and verify the password.

    Returns True if authenticated, False otherwise.
    Uses DASHBOARD_PASSWORD from environment.
    """
    if st.session_state.get("authenticated"):
        return True

    st.title("🔐 Restaurant Admin Login")

    password = st.text_input("Password", type="password")

    if st.button("Login"):
        expected = os.environ.get("DASHBOARD_PASSWORD", "admin")
        if password == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False
