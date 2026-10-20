"""
Booking service for space filtering, availability checks,
duration and price calculation, and conflict validation.
"""

import json
import random
import string
from datetime import datetime, date, time
from typing import List, Optional, Tuple, Dict, Any
from database.db import fetch_all, fetch_one, execute_insert


def get_spaces(
    category: Optional[str] = None,
    location: Optional[str] = None,
    max_price: Optional[float] = None,
    min_capacity: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve spaces with optional filtering."""
    query = "SELECT * FROM SPACES WHERE availability_status = 'AVAILABLE'"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if location and location != "All":
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    if max_price is not None and max_price > 0:
        query += " AND price <= ?"
        params.append(max_price)

    if min_capacity is not None and min_capacity > 0:
        query += " AND capacity >= ?"
        params.append(min_capacity)

    query += " ORDER BY id ASC"
    spaces = fetch_all(query, tuple(params))
    for sp in spaces:
        try:
            sp["amenities_list"] = json.loads(sp["amenities"])
        except Exception:
            sp["amenities_list"] = [a.strip() for a in sp["amenities"].split(",") if a.strip()]
    return spaces


def get_space_by_id(space_id: int) -> Optional[Dict[str, Any]]:
    """Fetch space details by ID."""
    space = fetch_one("SELECT * FROM SPACES WHERE id = ?", (space_id,))
    if space:
        try:
            space["amenities_list"] = json.loads(space["amenities"])
        except Exception:
            space["amenities_list"] = [a.strip() for a in space["amenities"].split(",") if a.strip()]
    return space


def calculate_booking_duration_and_amount(
    space_rate: float,
    category: str,
    start_time_str: str,
    end_time_str: str,
) -> Tuple[float, float]:
    """
    Calculate duration in hours and total amount.
    Returns (duration_hours, total_amount).
    """
    t_start = datetime.strptime(start_time_str, "%H:%M")
    t_end = datetime.strptime(end_time_str, "%H:%M")

    diff_seconds = (t_end - t_start).total_seconds()
    duration_hours = max(0.0, diff_seconds / 3600.0)

    if category == "Day Pass":
        # Day pass is flat daily rate
        total_amount = space_rate
    else:
        total_amount = round(duration_hours * space_rate, 2)

    return round(duration_hours, 2), total_amount


def check_booking_conflict(
    space_id: int,
    booking_date: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if a booking slot conflicts with existing confirmed bookings.
    Overlapping rule: existing.start < new.end AND existing.end > new.start.
    Returns (has_conflict, conflict_message).
    """
    query = """
        SELECT id, booking_reference, start_time, end_time 
        FROM BOOKINGS 
        WHERE space_id = ? 
          AND booking_date = ? 
          AND status = 'CONFIRMED'
          AND start_time < ? 
          AND end_time > ?
    """
    params = [space_id, booking_date, end_time, start_time]

    if exclude_booking_id:
        query += " AND id != ?"
        params.append(exclude_booking_id)

    conflicts = fetch_all(query, tuple(params))
    if conflicts:
        conflict_ref = conflicts[0]["booking_reference"]
        c_start = conflicts[0]["start_time"]
        c_end = conflicts[0]["end_time"]
        return True, f"Time slot unavailable: Overlaps with existing booking {conflict_ref} ({c_start} - {c_end})."

    return False, None


def generate_booking_reference() -> str:
    """Generate unique readable booking reference (e.g. BK-2026-9481)."""
    year = datetime.now().year
    suffix = "".join(random.choices(string.digits, k=4))
    ref = f"BK-{year}-{suffix}"
    # Verify uniqueness
    while fetch_one("SELECT id FROM BOOKINGS WHERE booking_reference = ?", (ref,)):
        suffix = "".join(random.choices(string.digits, k=4))
        ref = f"BK-{year}-{suffix}"
    return ref


def create_booking(
    customer_id: int,
    space_id: int,
    booking_date: str,
    start_time: str,
    end_time: str,
    number_of_people: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validate and persist a workspace reservation.
    Returns (success, message, booking_dict).
    """
    space = get_space_by_id(space_id)
    if not space:
        return False, "Selected space does not exist.", None

    if space["availability_status"] != "AVAILABLE":
        return False, f"Space is currently {space['availability_status'].lower()} and not open for booking.", None

    # Capacity check
    if number_of_people > space["capacity"]:
        return (
            False,
            f"The selected space has a maximum capacity of {space['capacity']} people. You entered {number_of_people}.",
            None,
        )

    # Date check
    try:
        b_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        if b_date < date.today():
            return False, "Booking date cannot be in the past.", None
    except ValueError:
        return False, "Invalid date format. Expected YYYY-MM-DD.", None

    # Time validation
    try:
        t_start = datetime.strptime(start_time, "%H:%M")
        t_end = datetime.strptime(end_time, "%H:%M")
        if t_end <= t_start:
            return False, "End time must be strictly later than start time.", None
    except ValueError:
        return False, "Invalid time format. Expected HH:MM.", None

    # Overlap check
    has_conflict, conflict_msg = check_booking_conflict(space_id, booking_date, start_time, end_time)
    if has_conflict:
        return False, conflict_msg, None

    # Calculate pricing
    duration_hours, total_amount = calculate_booking_duration_and_amount(
        space["price"], space["category"], start_time, end_time
    )

    if duration_hours <= 0:
        return False, "Booking duration must be greater than zero.", None

    booking_ref = generate_booking_reference()

    try:
        booking_id = execute_insert(
            """INSERT INTO BOOKINGS 
            (booking_reference, customer_id, space_id, booking_date, start_time, end_time, booking_amount, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFIRMED')""",
            (booking_ref, customer_id, space_id, booking_date, start_time, end_time, total_amount),
        )

        booking_data = fetch_one(
            """SELECT b.*, s.name as space_name, s.category, s.location, s.image_path, s.amenities
            FROM BOOKINGS b
            JOIN SPACES s ON b.space_id = s.id
            WHERE b.id = ?""",
            (booking_id,),
        )
        return True, "Your booking has been confirmed!", booking_data

    except Exception as e:
        return False, f"Failed to save booking: {str(e)}", None


def get_customer_bookings(customer_id: int) -> List[Dict[str, Any]]:
    """Retrieve all bookings belonging to a specific customer with space details."""
    query = """
        SELECT b.*, s.name as space_name, s.category, s.location, s.image_path, s.amenities,
               c.id as complaint_id, c.complaint_reference, c.status as complaint_status
        FROM BOOKINGS b
        JOIN SPACES s ON b.space_id = s.id
        LEFT JOIN COMPLAINTS c ON b.id = c.booking_id
        WHERE b.customer_id = ?
        ORDER BY b.booking_date DESC, b.start_time DESC
    """
    bookings = fetch_all(query, (customer_id,))
    for bk in bookings:
        try:
            bk["amenities_list"] = json.loads(bk["amenities"])
        except Exception:
            bk["amenities_list"] = [a.strip() for a in bk["amenities"].split(",") if a.strip()]
    return bookings


# ----------------------------------------------------------------------
# Slot search helpers used by the Home page filters and the booking dialog
# ----------------------------------------------------------------------
OPENING_HOUR = 8
CLOSING_HOUR = 22


def get_free_start_times(space_id: int, booking_date: str, duration_hours: int) -> List[str]:
    """
    Return the start times ("HH:00") at which `duration_hours` fit between opening and
    closing time without overlapping a confirmed booking (and not in the past for today).
    """
    duration_hours = int(duration_hours)
    if duration_hours < 1:
        return []

    try:
        day = datetime.strptime(booking_date, "%Y-%m-%d").date()
    except ValueError:
        return []
    if day < date.today():
        return []

    now_hour = datetime.now().hour if day == date.today() else -1

    free = []
    for hour in range(OPENING_HOUR, CLOSING_HOUR - duration_hours + 1):
        if hour <= now_hour:
            continue
        start = f"{hour:02d}:00"
        end = f"{hour + duration_hours:02d}:00"
        has_conflict, _ = check_booking_conflict(space_id, booking_date, start, end)
        if not has_conflict:
            free.append(start)
    return free


def search_available_spaces(
    booking_date: str,
    duration_hours: int,
    category: Optional[str] = None,
    max_total_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Find spaces that match the Home page filters and still have a free slot.

    Returns {"spaces": [...sorted cheapest first...], "fully_booked": int}.
    Each space gets `estimated_total` and `free_slots`.
    """
    candidates = get_spaces(category=category)
    matches, fully_booked = [], 0

    for sp in candidates:
        slots = get_free_start_times(sp["id"], booking_date, duration_hours)
        if not slots:
            fully_booked += 1
            continue

        end_guess = f"{int(slots[0][:2]) + int(duration_hours):02d}:00"
        _, total = calculate_booking_duration_and_amount(sp["price"], sp["category"], slots[0], end_guess)

        if max_total_price and total > max_total_price:
            continue

        sp["estimated_total"] = total
        sp["free_slots"] = slots
        matches.append(sp)

    matches.sort(key=lambda s: (s["estimated_total"], s["name"]))
    return {"spaces": matches, "fully_booked": fully_booked}
