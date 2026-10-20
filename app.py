"""
CoWorkHub — Coworking Space Booking & AI-assisted Complaint Resolution.
Main application entry point and router.
"""

import sys
from pathlib import Path
import streamlit as st

# Configure sys.path so project modules resolve reliably
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db import get_db_path, init_db, ensure_schema_upgrades
from database.seed_data import seed_database
from components.styles import apply_custom_styles
from components.navigation import (
    init_session_state,
    render_navbar,
    check_page_authorization,
    navigate_to,
    show_flash,
)
from pages.auth_pages import render_auth_page

st.set_page_config(
    page_title="CoWorkHub",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOMER_PAGES = {"home", "my_bookings", "my_complaints", "chat_assistant"}
ADMIN_PAGES = {"admin_dashboard", "admin_investigation"}


@st.cache_resource
def ensure_database_ready():
    """Create/seed the SQLite database on first run and apply small upgrades."""
    if not get_db_path().exists():
        seed_database()
    ensure_schema_upgrades()
    return True


def main():
    ensure_database_ready()
    apply_custom_styles()
    init_session_state()

    page = st.session_state.get("current_page", "auth")
    user = st.session_state.get("user")

    # Signed-in users never see the login page; signed-out users never see anything else
    if page == "auth" and user:
        page = "admin_dashboard" if user["role"] == "ADMIN" else "home"
        st.session_state["current_page"] = page
    if page != "auth" and not user:
        st.session_state["current_page"] = "auth"
        page = "auth"

    render_navbar()
    show_flash()

    if page == "auth":
        render_auth_page()

    elif page in CUSTOMER_PAGES:
        if not check_page_authorization("CUSTOMER"):
            return
        if page == "home":
            from pages.home import render_home
            render_home()
        elif page == "my_bookings":
            from pages.my_bookings import render_my_bookings
            render_my_bookings()
        elif page == "my_complaints":
            from pages.my_complaints import render_my_complaints
            render_my_complaints()
        elif page == "chat_assistant":
            from pages.chat_assistant import render_chat_assistant
            render_chat_assistant()

    elif page in ADMIN_PAGES:
        if not check_page_authorization("ADMIN"):
            return
        if page == "admin_dashboard":
            from pages.admin_dashboard import render_admin_dashboard
            render_admin_dashboard()
        else:
            from pages.dispute_details import render_dispute_details
            render_dispute_details()

    else:
        navigate_to("auth")


if __name__ == "__main__":
    main()
