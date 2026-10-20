"""
Home page: quick filters (date, duration, category, budget) and suggested rooms.
Clicking "Book now" opens a booking dialog where the slot is confirmed.
"""

from datetime import date, timedelta
from pathlib import Path
import streamlit as st
from services.booking_service import (
    search_available_spaces,
    get_free_start_times,
    calculate_booking_duration_and_amount,
    create_booking,
)
from components.navigation import navigate_to, set_flash

BASE_DIR = Path(__file__).resolve().parent.parent
CATEGORIES = ["All", "Meeting Room", "Private Cabin", "Dedicated Desk", "Studio", "Day Pass"]
BUDGET_OPTIONS = {"Any budget": None, "Up to ₹500": 500, "Up to ₹1,000": 1000, "Up to ₹2,000": 2000, "Up to ₹5,000": 5000}


def _plus_hours(start: str, hours: int) -> str:
    return f"{int(start[:2]) + int(hours):02d}:00"


@st.dialog("Book this space", width="large")
def booking_dialog(space: dict, default_date: date, default_duration: int):
    """Confirm date, time and price for the chosen room."""
    sid = space["id"]
    col_img, col_info = st.columns([1, 1.4])
    with col_img:
        img = BASE_DIR / space["image_path"]
        if img.exists():
            st.image(str(img), width="stretch")
    with col_info:
        st.markdown(f"### {space['name']}")
        st.markdown(f"<div class='room-meta'>{space['category']} · 📍 {space['location']} · 👥 up to {space['capacity']}</div>", unsafe_allow_html=True)
        st.markdown("".join(f"<span class='chip'>{a}</span>" for a in space["amenities_list"]), unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        booking_date = st.date_input("Date", value=default_date, min_value=date.today(), key=f"bk_date_{sid}")
    with c2:
        duration = st.number_input("Hours", min_value=1, max_value=8, value=int(default_duration), key=f"bk_dur_{sid}")
    with c3:
        guests = st.number_input("Guests", min_value=1, max_value=space["capacity"], value=min(2, space["capacity"]), key=f"bk_guests_{sid}")

    date_str = booking_date.strftime("%Y-%m-%d")
    slots = get_free_start_times(sid, date_str, duration)

    if not slots:
        st.warning("No free slot for that date and length. Try another date or fewer hours.")
        return

    start = st.selectbox("Start time", slots, key=f"bk_start_{sid}")
    end = _plus_hours(start, duration)
    hours, total = calculate_booking_duration_and_amount(space["price"], space["category"], start, end)
    rate_unit = "day" if space["category"] == "Day Pass" else "hour"

    st.markdown(
        f"""
        <div class="summary-box">
            <div class="summary-row"><span>Date</span><strong>{booking_date.strftime('%a, %d %b %Y')}</strong></div>
            <div class="summary-row"><span>Time</span><strong>{start} – {end} ({hours:g} hrs)</strong></div>
            <div class="summary-row"><span>Rate</span><span>₹{space['price']:,.0f} / {rate_unit}</span></div>
            <div class="summary-row summary-total"><span>Amount</span><span>₹{total:,.0f}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Confirm & reserve", type="primary", width="stretch", key=f"bk_confirm_{sid}"):
        ok, msg, booking = create_booking(
            customer_id=st.session_state["user"]["id"],
            space_id=sid,
            booking_date=date_str,
            start_time=start,
            end_time=end,
            number_of_people=int(guests),
        )
        if ok:
            set_flash(f"Booked {booking['space_name']} · {booking['booking_reference']}", "🎉")
            navigate_to("my_bookings")
        else:
            st.error(msg)


def _room_card(space: dict, duration: int, best: bool, default_date: date):
    with st.container(border=True):
        img = BASE_DIR / space["image_path"]
        if img.exists():
            st.image(str(img), width="stretch")

        st.markdown(f"**{space['name']}**" + (" <span class='chip chip-best'>Best value</span>" if best else ""), unsafe_allow_html=True)
        st.markdown(f"<div class='room-meta'>{space['category']} · 📍 {space['location']} · 👥 {space['capacity']}</div>", unsafe_allow_html=True)
        st.markdown("".join(f"<span class='chip'>{a}</span>" for a in space["amenities_list"][:3]), unsafe_allow_html=True)

        label = "full day" if space["category"] == "Day Pass" else f"{duration} hr{'s' if duration > 1 else ''}"
        st.markdown(f"<div class='room-price'>₹{space['estimated_total']:,.0f} <small>for {label}</small></div>", unsafe_allow_html=True)

        if st.button("Book now", key=f"book_{space['id']}", type="primary", width="stretch"):
            booking_dialog(space, default_date, duration)


def render_home():
    st.markdown("<h1 class='page-title'>Find your space</h1><div class='page-sub'>Pick a day and we'll show the rooms that are free.</div>", unsafe_allow_html=True)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            pick_date = st.date_input("Date", value=date.today() + timedelta(days=1), min_value=date.today(), key="f_date")
        with c2:
            duration = st.selectbox("Duration", list(range(1, 9)), index=1, format_func=lambda h: f"{h} hour{'s' if h > 1 else ''}", key="f_duration")
        with c3:
            category = st.selectbox("Space type", CATEGORIES, key="f_category")
        with c4:
            budget_label = st.selectbox("Budget", list(BUDGET_OPTIONS.keys()), key="f_budget")

    result = search_available_spaces(
        booking_date=pick_date.strftime("%Y-%m-%d"),
        duration_hours=int(duration),
        category=None if category == "All" else category,
        max_total_price=BUDGET_OPTIONS[budget_label],
    )
    spaces = result["spaces"]

    st.markdown("### Suggested for you")
    if not spaces:
        msg = "No rooms match these filters."
        if result["fully_booked"]:
            msg += f" {result['fully_booked']} room(s) are fully booked for that day."
        st.info(msg + " Try another date, fewer hours or a higher budget.")
        return

    note = f" · {result['fully_booked']} fully booked" if result["fully_booked"] else ""
    st.caption(f"{len(spaces)} room(s) available on {pick_date.strftime('%d %b')}{note}")

    cols = st.columns(3)
    for i, sp in enumerate(spaces):
        with cols[i % 3]:
            _room_card(sp, int(duration), best=(i == 0 and len(spaces) > 1), default_date=pick_date)
