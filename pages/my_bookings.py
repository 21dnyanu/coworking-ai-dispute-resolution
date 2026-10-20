"""
My Bookings: the customer's reservations with details and a "Raise complaint" action.
"""

from pathlib import Path
import streamlit as st
from services.booking_service import get_customer_bookings
from components.navigation import navigate_to
from components.styles import get_status_badge_html
from components.complaint_form import render_complaint_form

BASE_DIR = Path(__file__).resolve().parent.parent


@st.dialog("Raise a complaint", width="large")
def complaint_dialog(booking: dict):
    render_complaint_form(booking, st.session_state["user"])


def render_my_bookings():
    user = st.session_state["user"]
    bookings = get_customer_bookings(user["id"])

    st.markdown("<h1 class='page-title'>My bookings</h1><div class='page-sub'>Your reservations. Something went wrong? Raise a complaint from here.</div>", unsafe_allow_html=True)

    if not bookings:
        st.info("You haven't booked anything yet.")
        if st.button("Find a space", type="primary"):
            navigate_to("home")
        return

    for bk in bookings:
        with st.container(border=True):
            col_img, col_info, col_amt, col_act = st.columns([1, 3, 1.2, 1.6])

            with col_img:
                img = BASE_DIR / bk["image_path"]
                if img.exists():
                    st.image(str(img), width="stretch")

            with col_info:
                st.markdown(f"**{bk['space_name']}** &nbsp; {get_status_badge_html(bk['status'])}", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='room-meta'>{bk['category']} · 📍 {bk['location']}<br>"
                    f"📅 {bk['booking_date']} · ⏰ {bk['start_time']} – {bk['end_time']} · Ref <code>{bk['booking_reference']}</code></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("".join(f"<span class='chip'>{a}</span>" for a in bk["amenities_list"]), unsafe_allow_html=True)

            with col_amt:
                st.markdown(f"<div class='room-meta'>Amount</div><div class='room-price'>₹{bk['booking_amount']:,.0f}</div>", unsafe_allow_html=True)

            with col_act:
                if bk.get("complaint_id"):
                    st.markdown(
                        f"<div class='room-meta'>Complaint</div>{get_status_badge_html(bk['complaint_status'])}",
                        unsafe_allow_html=True,
                    )
                    if st.button("View complaint", key=f"vc_{bk['id']}", width="stretch"):
                        navigate_to("my_complaints")
                elif bk["status"] == "CANCELLED":
                    st.caption("Cancelled bookings can't be reported.")
                else:
                    if st.button("Raise complaint", key=f"rc_{bk['id']}", width="stretch"):
                        complaint_dialog(bk)
