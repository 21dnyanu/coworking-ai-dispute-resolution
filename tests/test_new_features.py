"""Tests for the redesigned flow: slot search, chat helpers, admin dashboard data."""

from datetime import date, timedelta

from database.db import fetch_one
from services.booking_service import (
    create_booking,
    get_free_start_times,
    search_available_spaces,
)
from services.chat_service import (
    detect_category,
    is_status_question,
    format_status_reply,
)
from services.complaint_service import create_complaint
from components.labels import recommended_amount, resolution_label
from pages.admin_dashboard import load_case_rows, ai_recommendation_text, admin_decision_text, get_admin_metrics


def _future(days=30) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def _customer_id(email="alice@example.com") -> int:
    return fetch_one("SELECT id FROM USERS WHERE email = ?", (email,))["id"]


def _space(category="Meeting Room") -> dict:
    return fetch_one("SELECT * FROM SPACES WHERE category = ? AND availability_status = 'AVAILABLE'", (category,))


def test_free_slots_exclude_booked_hours():
    space, day = _space(), _future()
    before = get_free_start_times(space["id"], day, 2)
    assert "10:00" in before

    ok, msg, _ = create_booking(_customer_id(), space["id"], day, "10:00", "12:00", 1)
    assert ok, msg

    after = get_free_start_times(space["id"], day, 2)
    # 09:00-11:00, 10:00-12:00 and 11:00-13:00 overlap the new booking; 12:00 is free again
    assert "09:00" not in after and "10:00" not in after and "11:00" not in after
    assert "12:00" in after and "08:00" in after


def test_free_slots_empty_for_past_or_bad_input():
    space = _space()
    assert get_free_start_times(space["id"], "2020-01-01", 2) == []
    assert get_free_start_times(space["id"], "not-a-date", 2) == []
    assert get_free_start_times(space["id"], _future(), 0) == []
    assert get_free_start_times(space["id"], _future(), 15) == []  # longer than opening hours


def test_search_filters_by_category_budget_and_sorts_by_price():
    result = search_available_spaces(_future(), 2)
    totals = [s["estimated_total"] for s in result["spaces"]]
    assert result["spaces"] and totals == sorted(totals)

    only_rooms = search_available_spaces(_future(), 2, category="Meeting Room")["spaces"]
    assert only_rooms and all(s["category"] == "Meeting Room" for s in only_rooms)

    cheap = search_available_spaces(_future(), 2, max_total_price=400)["spaces"]
    assert all(s["estimated_total"] <= 400 for s in cheap)


def test_search_hides_fully_booked_space():
    space, day = _space(), _future(45)
    for start, end in [("08:00", "12:00"), ("12:00", "16:00"), ("16:00", "20:00"), ("20:00", "22:00")]:
        ok, msg, _ = create_booking(_customer_id("bob@example.com"), space["id"], day, start, end, 1)
        assert ok, msg
    result = search_available_spaces(day, 2, category=space["category"])
    assert space["id"] not in [s["id"] for s in result["spaces"]]
    assert result["fully_booked"] >= 1


def test_chat_category_detection():
    assert detect_category("The projector did not turn on") == "Broken Equipment"
    assert detect_category("wifi keeps disconnecting") == "Wi-Fi Problem"
    assert detect_category("I was locked out of my cabin") == "Access Denied"
    assert detect_category("it was extremely noisy") == "Noise Problem"
    assert detect_category("something happened") == "Other"


def test_chat_status_question_and_reply():
    assert is_status_question("What is the status of my complaint?")
    assert not is_status_question("The projector is broken")
    assert "haven't raised" in format_status_reply([])
    reply = format_status_reply([{"complaint_reference": "CMP-1", "category": "Wi-Fi Problem", "status": "UNDER REVIEW", "final_resolution": None}])
    assert "CMP-1" in reply and "Under Review" in reply


def test_recommended_amount_never_invents_percentages():
    assert recommended_amount("FULL_REFUND", 1000, None) == 1000
    assert recommended_amount("NO_REFUND", 1000, None) == 0
    assert recommended_amount("PARTIAL_REFUND", 1000, 500, "") == 500
    assert recommended_amount("PARTIAL_REFUND", 1000, None, "refund of ₹1,250.50 recommended") == 1250.5
    assert recommended_amount("PARTIAL_REFUND", 1000, None, "no amount quoted") is None
    assert recommended_amount("MANUAL_INVESTIGATION", 1000, None) is None
    assert resolution_label("MANUAL_INVESTIGATION") == "Manual review"


def test_new_complaint_gets_ai_recommendation_visible_to_admin():
    alice = _customer_id()
    space, day = _space(), _future(60)
    ok, msg, booking = create_booking(alice, space["id"], day, "10:00", "12:00", 1)
    assert ok, msg

    ok, msg, complaint = create_complaint(alice, booking["id"], "Broken Equipment", "The projector would not turn on at all.", "Partial Refund")
    assert ok, msg

    rows = {r["complaint_reference"]: r for r in load_case_rows()}
    row = rows[complaint["complaint_reference"]]
    assert row["customer_id"] == alice
    assert row["ai_resolution"] in ("FULL_REFUND", "PARTIAL_REFUND", "NO_REFUND", "MANUAL_INVESTIGATION")
    assert ai_recommendation_text(row) != "Pending"
    assert admin_decision_text(row) == "Awaiting decision"  # humans decide, AI never finalises


def test_admin_metrics_and_filters():
    metrics = get_admin_metrics()
    assert metrics["total_complaints"] >= 4
    resolved = load_case_rows(status="RESOLVED")
    assert resolved and all(r["status"] == "RESOLVED" for r in resolved)
    assert load_case_rows(search="no-such-customer-xyz") == []
