"""
Unit tests for complaint submission, ownership enforcement, and duplicate checks.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.complaint_service import create_complaint, get_customer_complaints, get_complaint_details
from services.booking_service import create_booking
from database.seed_data import seed_database
from database.db import fetch_one


def test_create_complaint_success():
    """Test successful complaint submission for an eligible booking."""
    alice = fetch_one("SELECT id FROM USERS WHERE email = 'alice@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE id = 1")

    # Create a fresh booking for Alice
    target_date = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
    _, _, bk = create_booking(alice["id"], space["id"], target_date, "10:00", "12:00", 2)

    success, msg, cmp = create_complaint(
        customer_id=alice["id"],
        booking_id=bk["id"],
        category="Wi-Fi Problem",
        description="The Wi-Fi network kept dropping packets repeatedly during my call.",
        expected_resolution="Partial Refund",
    )
    assert success is True
    assert cmp is not None
    assert cmp["complaint_reference"].startswith("CMP-")
    assert cmp["status"] == "SUBMITTED"


def test_complaint_ownership_enforcement():
    """Ensure customer cannot submit a complaint against another user's booking."""
    alice = fetch_one("SELECT id FROM USERS WHERE email = 'alice@example.com'")
    bob = fetch_one("SELECT id FROM USERS WHERE email = 'bob@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE id = 1")

    # Booking belongs to Alice
    target_date = (date.today() + timedelta(days=70)).strftime("%Y-%m-%d")
    _, _, bk = create_booking(alice["id"], space["id"], target_date, "14:00", "16:00", 2)

    # Bob attempts to submit complaint against Alice's booking
    success, msg, cmp = create_complaint(
        customer_id=bob["id"],
        booking_id=bk["id"],
        category="Cleanliness Problem",
        description="Unauthorized complaint attempt on someone else's space.",
        expected_resolution="Full Refund",
    )
    assert success is False
    assert "security violation" in msg.lower() or "only raise complaints for your own" in msg.lower()
    assert cmp is None


def test_duplicate_complaint_rejection():
    """Ensure duplicate complaint on the same booking is prevented."""
    # Seeded booking BK-2026-1001 already has complaint CMP-2026-001
    bk1 = fetch_one("SELECT * FROM BOOKINGS WHERE booking_reference = 'BK-2026-1001'")

    success, msg, _ = create_complaint(
        customer_id=bk1["customer_id"],
        booking_id=bk1["id"],
        category="Broken Equipment",
        description="Second duplicate complaint attempt for projector issue.",
        expected_resolution="Partial Refund",
    )
    assert success is False
    assert "already been submitted" in msg.lower()


def test_complaint_description_short_rejection():
    """Ensure too-short descriptions are rejected."""
    alice = fetch_one("SELECT id FROM USERS WHERE email = 'alice@example.com'")
    space = fetch_one("SELECT id FROM SPACES WHERE id = 1")
    target_date = (date.today() + timedelta(days=80)).strftime("%Y-%m-%d")
    _, _, bk = create_booking(alice["id"], space["id"], target_date, "11:00", "13:00", 2)

    success, msg, _ = create_complaint(
        customer_id=alice["id"],
        booking_id=bk["id"],
        category="Other",
        description="Bad room",  # < 10 chars
        expected_resolution="Other",
    )
    assert success is False
    assert "at least 10 characters" in msg.lower()
