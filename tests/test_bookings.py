"""
Unit tests for space browsing, pricing calculation, booking creation, and conflict detection.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.booking_service import (
    get_spaces,
    get_space_by_id,
    calculate_booking_duration_and_amount,
    check_booking_conflict,
    create_booking,
)
from database.seed_data import seed_database
from database.db import fetch_one


def test_get_spaces_filtering():
    """Test space catalog filtering by category and location."""
    all_spaces = get_spaces()
    assert len(all_spaces) >= 5

    meeting_rooms = get_spaces(category="Meeting Room")
    assert all(s["category"] == "Meeting Room" for s in meeting_rooms)

    mumbai_spaces = get_spaces(location="Mumbai")
    assert all("Mumbai" in s["location"] for s in mumbai_spaces)


def test_calculate_duration_and_amount():
    """Test pricing math for hourly and flat rate spaces."""
    # Hourly calculation: ₹500/hr for 3 hours = ₹1500
    duration, amt = calculate_booking_duration_and_amount(500.0, "Meeting Room", "10:00", "13:00")
    assert duration == 3.0
    assert amt == 1500.0

    # Day pass calculation: flat rate
    duration, amt = calculate_booking_duration_and_amount(400.0, "Day Pass", "09:00", "18:00")
    assert amt == 400.0


def test_create_booking_success():
    """Test valid booking creation."""
    customer = fetch_one("SELECT id FROM USERS WHERE email = 'alice@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE name = 'Meeting Room A'")

    target_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    success, msg, bk = create_booking(
        customer_id=customer["id"],
        space_id=space["id"],
        booking_date=target_date,
        start_time="09:00",
        end_time="11:00",
        number_of_people=4,
    )
    assert success is True, f"Failed with message: {msg}"
    assert bk is not None
    assert bk["booking_reference"].startswith("BK-")
    assert bk["booking_amount"] == 1000.0


def test_booking_conflict_rejection():
    """Test that overlapping reservations on the same space and date are rejected."""
    customer = fetch_one("SELECT id FROM USERS WHERE email = 'alice@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE name = 'Meeting Room A'")

    target_date = (date.today() + timedelta(days=40)).strftime("%Y-%m-%d")

    # First booking: 14:00 - 17:00
    s1, _, bk1 = create_booking(
        customer_id=customer["id"],
        space_id=space["id"],
        booking_date=target_date,
        start_time="14:00",
        end_time="17:00",
        number_of_people=3,
    )
    assert s1 is True

    # Overlapping booking: 15:00 - 18:00 (overlaps by 2 hours)
    s2, msg2, _ = create_booking(
        customer_id=customer["id"],
        space_id=space["id"],
        booking_date=target_date,
        start_time="15:00",
        end_time="18:00",
        number_of_people=2,
    )
    assert s2 is False
    assert "overlaps" in msg2.lower() or "unavailable" in msg2.lower()


def test_booking_capacity_exceeded():
    """Test that booking exceeding space capacity is rejected."""
    customer = fetch_one("SELECT id FROM USERS WHERE email = 'bob@example.com'")
    # Executive Cabin has capacity 2
    cabin = fetch_one("SELECT id, capacity FROM SPACES WHERE name = 'Executive Cabin 101'")

    target_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    success, msg, _ = create_booking(
        customer_id=customer["id"],
        space_id=cabin["id"],
        booking_date=target_date,
        start_time="10:00",
        end_time="12:00",
        number_of_people=cabin["capacity"] + 3,
    )
    assert success is False
    assert "maximum capacity" in msg.lower()


def test_booking_past_date_rejection():
    """Test that past dates are rejected."""
    customer = fetch_one("SELECT id FROM USERS WHERE email = 'bob@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE id = 1")

    success, msg, _ = create_booking(
        customer_id=customer["id"],
        space_id=space["id"],
        booking_date="2020-01-01",
        start_time="10:00",
        end_time="12:00",
        number_of_people=2,
    )
    assert success is False
    assert "cannot be in the past" in msg.lower()
