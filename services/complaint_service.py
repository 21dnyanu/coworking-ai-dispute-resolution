"""
Complaint management service.
Handles complaint submission, customer authorization checks,
evidence linking, and status transitions.
"""

import json
import random
import string
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from database.db import fetch_one, fetch_all, execute_insert, execute_query


def generate_complaint_reference() -> str:
    """Generate unique readable complaint reference (e.g. CMP-2026-4821)."""
    year = datetime.now().year
    suffix = "".join(random.choices(string.digits, k=4))
    ref = f"CMP-{year}-{suffix}"
    while fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = ?", (ref,)):
        suffix = "".join(random.choices(string.digits, k=4))
        ref = f"CMP-{year}-{suffix}"
    return ref


def create_complaint(
    customer_id: int,
    booking_id: int,
    category: str,
    description: str,
    expected_resolution: str,
    evidence_file_path: Optional[str] = None,
    original_filename: Optional[str] = None,
    validation_status: Optional[str] = None,
    validation_result: Optional[dict] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Submit a new complaint against a booking.
    Strictly verifies booking ownership before submission.
    """
    description = description.strip()
    if not description:
        return False, "Please describe the problem you experienced.", None

    if len(description) < 10:
        return False, "Please provide more detail in your problem description (at least 10 characters).", None

    # Check that booking exists and belongs to this customer
    booking = fetch_one("SELECT * FROM BOOKINGS WHERE id = ?", (booking_id,))
    if not booking:
        return False, "Associated booking does not exist.", None

    if booking["customer_id"] != customer_id:
        return False, "Security violation: You can only raise complaints for your own bookings.", None

    # Check if a complaint already exists for this booking
    existing_cmp = fetch_one("SELECT id, complaint_reference FROM COMPLAINTS WHERE booking_id = ?", (booking_id,))
    if existing_cmp:
        return (
            False,
            f"A complaint ({existing_cmp['complaint_reference']}) has already been submitted for this booking.",
            None,
        )

    ref = generate_complaint_reference()

    try:
        complaint_id = execute_insert(
            """INSERT INTO COMPLAINTS 
            (complaint_reference, booking_id, customer_id, category, description, expected_resolution, status) 
            VALUES (?, ?, ?, ?, ?, ?, 'SUBMITTED')""",
            (ref, booking_id, customer_id, category, description, expected_resolution),
        )

        # Record evidence if uploaded
        if evidence_file_path:
            val_stat = validation_status or "PENDING"
            val_res_str = json.dumps(validation_result) if validation_result else None
            orig_name = original_filename or "evidence.jpg"

            execute_insert(
                """INSERT INTO EVIDENCE 
                (complaint_id, file_path, original_filename, validation_status, validation_result) 
                VALUES (?, ?, ?, ?, ?)""",
                (complaint_id, evidence_file_path, orig_name, val_stat, val_res_str),
            )

        # Trigger AI investigation pipeline immediately so analysis is ready for review
        try:
            from services.investigation_service import generate_dispute_investigation
            generate_dispute_investigation(complaint_id)
        except Exception as inv_err:
            print(f"Investigation trigger warning: {inv_err}")

        complaint = fetch_one("SELECT * FROM COMPLAINTS WHERE id = ?", (complaint_id,))
        return True, "Your complaint has been submitted successfully.", complaint

    except Exception as e:
        return False, f"Failed to submit complaint: {str(e)}", None


def get_customer_complaints(customer_id: int) -> List[Dict[str, Any]]:
    """Retrieve all complaints submitted by a customer."""
    query = """
        SELECT c.*, b.booking_reference, b.booking_date, b.booking_amount,
               s.name as space_name, s.category as space_category,
               ad.action as final_decision_action, ad.final_resolution,
               ai.proposed_resolution as ai_recommendation
        FROM COMPLAINTS c
        JOIN BOOKINGS b ON c.booking_id = b.id
        JOIN SPACES s ON b.space_id = s.id
        LEFT JOIN ADMIN_DECISIONS ad ON c.id = ad.complaint_id
        LEFT JOIN AI_INVESTIGATIONS ai ON c.id = ai.complaint_id
        WHERE c.customer_id = ?
        ORDER BY c.created_at DESC
    """
    return fetch_all(query, (customer_id,))


def get_complaint_details(complaint_id: int) -> Optional[Dict[str, Any]]:
    """Fetch complete complaint record including booking, evidence, and investigation."""
    query = """
        SELECT c.*, 
               b.booking_reference, b.booking_date, b.start_time, b.end_time, b.booking_amount,
               u.full_name as customer_name, u.email as customer_email,
               s.id as space_id, s.name as space_name, s.category as space_category,
               s.location as space_location, s.amenities as space_amenities,
               os.statement as owner_statement
        FROM COMPLAINTS c
        JOIN BOOKINGS b ON c.booking_id = b.id
        JOIN USERS u ON c.customer_id = u.id
        JOIN SPACES s ON b.space_id = s.id
        LEFT JOIN OWNER_STATEMENTS os ON c.id = os.complaint_id
        WHERE c.id = ?
    """
    complaint = fetch_one(query, (complaint_id,))
    if not complaint:
        return None

    try:
        complaint["amenities_list"] = json.loads(complaint["space_amenities"])
    except Exception:
        complaint["amenities_list"] = [a.strip() for a in complaint["space_amenities"].split(",") if a.strip()]

    # Evidence
    evidence = fetch_all("SELECT * FROM EVIDENCE WHERE complaint_id = ?", (complaint_id,))
    for ev in evidence:
        if ev.get("validation_result"):
            try:
                ev["parsed_result"] = json.loads(ev["validation_result"])
            except Exception:
                ev["parsed_result"] = None
    complaint["evidence_list"] = evidence

    # AI Investigation
    inv = fetch_one("SELECT * FROM AI_INVESTIGATIONS WHERE complaint_id = ?", (complaint_id,))
    if inv:
        for field in [
            "verified_facts_json",
            "customer_allegations_json",
            "owner_allegations_json",
            "unknown_information_json",
            "evidence_analysis_json",
            "policy_references_json",
        ]:
            try:
                inv[field.replace("_json", "")] = json.loads(inv[field])
            except Exception:
                inv[field.replace("_json", "")] = []
    complaint["ai_investigation"] = inv

    # Admin Decision
    decision = fetch_one(
        """SELECT ad.*, u.full_name as admin_name 
        FROM ADMIN_DECISIONS ad 
        JOIN USERS u ON ad.admin_id = u.id 
        WHERE ad.complaint_id = ?""",
        (complaint_id,),
    )
    complaint["admin_decision"] = decision

    return complaint


def add_or_replace_evidence(
    complaint_id: int,
    file_path: str,
    original_filename: str,
    validation_status: str,
    validation_result: Optional[dict] = None,
) -> bool:
    """Attach new or replacement evidence to a complaint, transition status, and re-run investigation."""
    try:
        val_res_str = json.dumps(validation_result) if validation_result else None
        
        # Check if evidence exists
        existing = fetch_one("SELECT id FROM EVIDENCE WHERE complaint_id = ?", (complaint_id,))
        if existing:
            execute_query(
                """UPDATE EVIDENCE 
                SET file_path = ?, original_filename = ?, validation_status = ?, validation_result = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?""",
                (file_path, original_filename, validation_status, val_res_str, existing["id"]),
            )
        else:
            execute_insert(
                """INSERT INTO EVIDENCE 
                (complaint_id, file_path, original_filename, validation_status, validation_result) 
                VALUES (?, ?, ?, ?, ?)""",
                (complaint_id, file_path, original_filename, validation_status, val_res_str),
            )

        # Update complaint status from AWAITING EVIDENCE back to UNDER REVIEW
        execute_query(
            "UPDATE COMPLAINTS SET status = 'UNDER REVIEW' WHERE id = ? AND status = 'AWAITING EVIDENCE'",
            (complaint_id,),
        )

        # Re-trigger AI investigation pipeline with the new evidence
        try:
            from services.investigation_service import generate_dispute_investigation
            generate_dispute_investigation(complaint_id)
        except Exception as inv_err:
            print(f"Investigation re-trigger warning: {inv_err}")

        return True
    except Exception as e:
        print(f"Error adding replacement evidence: {e}")
        return False

