"""
Database seeding script with idempotent demo data.
Seeds sample users, coworking spaces, bookings, complaints, evidence,
owner statements, and policy documents.
"""

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from werkzeug.security import generate_password_hash
from database.db import get_db_connection, init_db, fetch_one, execute_query


def seed_database():
    """Seed the database with required demonstration records."""
    print("Initializing database schema...")
    init_db()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Seed Users (Admin and Customers)
        users = [
            ("System Administrator", "admin@coworking.com", "Admin@123", "ADMIN"),
            ("Alice Johnson", "alice@example.com", "Password@123", "CUSTOMER"),
            ("Bob Smith", "bob@example.com", "Password@123", "CUSTOMER"),
            ("Charlie Davis", "charlie@example.com", "Password@123", "CUSTOMER"),
        ]

        for name, email, raw_pwd, role in users:
            existing = cursor.execute("SELECT id FROM USERS WHERE email = ?", (email,)).fetchone()
            if not existing:
                pwd_hash = generate_password_hash(raw_pwd)
                cursor.execute(
                    "INSERT INTO USERS (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (name, email, pwd_hash, role),
                )
                print(f"Created user: {email} ({role})")

        # 2. Seed Coworking Spaces (At least 5)
        spaces = [
            (
                "Meeting Room A",
                "Meeting Room",
                "Navi Mumbai, Sector 15",
                "Modern 6-person meeting room equipped with an HD projector, magnetic whiteboard, and ergonomic seating.",
                500.0,
                6,
                json.dumps(["Wi-Fi", "Projector", "Whiteboard", "Air Conditioning", "Power Sockets"]),
                "sample_images/space_meeting_room_a.png",
                "AVAILABLE",
            ),
            (
                "Executive Cabin 101",
                "Private Cabin",
                "Mumbai BKC, G-Block",
                "Premium soundproof cabin for up to 2 professionals with smart digital door lock and dual monitors.",
                800.0,
                2,
                json.dumps(["Wi-Fi", "Smart Lock Access", "Dual Monitors", "Air Conditioning", "Ergonomic Chairs"]),
                "sample_images/space_exec_cabin.png",
                "AVAILABLE",
            ),
            (
                "Dedicated Quiet Desk #12",
                "Dedicated Desk",
                "Pune Baner, High Street",
                "Quiet personal dedicated desk with locking filing cabinet, ergonomic chair, and dedicated high-speed LAN.",
                150.0,
                1,
                json.dumps(["High-speed LAN", "Ergonomic Chair", "Locker", "Power Backup", "Cafeteria Access"]),
                "sample_images/space_dedicated_desk.png",
                "AVAILABLE",
            ),
            (
                "Creative Media Studio B",
                "Studio",
                "Bengaluru Koramangala",
                "Acoustically treated studio space with 4K camera setup, studio lights, and podcasting microphones.",
                1200.0,
                8,
                json.dumps(["Acoustic Treatment", "4K Video Rig", "Studio Lighting", "Podcasting Mics", "High-speed Wi-Fi"]),
                "sample_images/space_media_studio.png",
                "AVAILABLE",
            ),
            (
                "Open Hot Desk Day Pass",
                "Day Pass",
                "Mumbai Andheri West",
                "Flexible all-day hot desk access with unlimited premium coffee, ultra-fast Wi-Fi, and lounge areas.",
                400.0,
                1,
                json.dumps(["High-speed Wi-Fi", "Unlimited Coffee", "Lounge Access", "Power Sockets", "Printing Quota"]),
                "sample_images/space_day_pass.png",
                "AVAILABLE",
            ),
        ]

        for name, cat, loc, desc, price, cap, amens, img, status in spaces:
            existing = cursor.execute("SELECT id FROM SPACES WHERE name = ?", (name,)).fetchone()
            if not existing:
                cursor.execute(
                    """INSERT INTO SPACES 
                    (name, category, location, description, price, capacity, amenities, image_path, availability_status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, cat, loc, desc, price, cap, amens, img, status),
                )
                print(f"Created space: {name}")

        # Fetch IDs for references
        alice = cursor.execute("SELECT id FROM USERS WHERE email = 'alice@example.com'").fetchone()[0]
        bob = cursor.execute("SELECT id FROM USERS WHERE email = 'bob@example.com'").fetchone()[0]
        charlie = cursor.execute("SELECT id FROM USERS WHERE email = 'charlie@example.com'").fetchone()[0]

        space1 = cursor.execute("SELECT id FROM SPACES WHERE name = 'Meeting Room A'").fetchone()[0]
        space2 = cursor.execute("SELECT id FROM SPACES WHERE name = 'Executive Cabin 101'").fetchone()[0]
        space3 = cursor.execute("SELECT id FROM SPACES WHERE name = 'Dedicated Quiet Desk #12'").fetchone()[0]
        space5 = cursor.execute("SELECT id FROM SPACES WHERE name = 'Open Hot Desk Day Pass'").fetchone()[0]

        # 3. Seed Bookings (At least 3 demo bookings)
        bookings = [
            ("BK-2026-1001", alice, space1, "2026-10-22", "10:00", "13:00", 1500.0, "CONFIRMED"),
            ("BK-2026-1002", bob, space2, "2026-10-23", "14:00", "17:00", 2400.0, "CONFIRMED"),
            ("BK-2026-1003", charlie, space5, "2026-10-24", "09:00", "18:00", 400.0, "CONFIRMED"),
            ("BK-2026-1004", alice, space3, "2026-10-18", "09:00", "17:00", 1200.0, "COMPLETED"),
        ]

        for ref, cust_id, sp_id, b_date, s_time, e_time, amt, st in bookings:
            existing = cursor.execute("SELECT id FROM BOOKINGS WHERE booking_reference = ?", (ref,)).fetchone()
            if not existing:
                cursor.execute(
                    """INSERT INTO BOOKINGS 
                    (booking_reference, customer_id, space_id, booking_date, start_time, end_time, booking_amount, status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ref, cust_id, sp_id, b_date, s_time, e_time, amt, st),
                )
                print(f"Created booking: {ref}")

        bk1 = cursor.execute("SELECT id FROM BOOKINGS WHERE booking_reference = 'BK-2026-1001'").fetchone()[0]
        bk2 = cursor.execute("SELECT id FROM BOOKINGS WHERE booking_reference = 'BK-2026-1002'").fetchone()[0]
        bk3 = cursor.execute("SELECT id FROM BOOKINGS WHERE booking_reference = 'BK-2026-1003'").fetchone()[0]
        bk4 = cursor.execute("SELECT id FROM BOOKINGS WHERE booking_reference = 'BK-2026-1004'").fetchone()[0]

        # 4. Seed Policy Documents
        policies = [
            ("Amenity Malfunction and Service Outage Policy", "knowledge_base/policies/amenity_malfunction_policy.txt", "1.2"),
            ("Space Access and Entry Lockout Policy", "knowledge_base/policies/access_and_keycard_policy.txt", "1.1"),
            ("Cancellation, Rescheduling, and Standard Refund Schedule", "knowledge_base/policies/cancellation_and_refund_policy.txt", "2.0"),
            ("Property Damage and Security Deposit Policy", "knowledge_base/policies/property_damage_and_liability_policy.txt", "1.0"),
        ]

        for doc_name, doc_path, ver in policies:
            existing = cursor.execute("SELECT id FROM POLICY_DOCUMENTS WHERE document_name = ?", (doc_name,)).fetchone()
            if not existing:
                cursor.execute(
                    "INSERT INTO POLICY_DOCUMENTS (document_name, document_path, version) VALUES (?, ?, ?)",
                    (doc_name, doc_path, ver),
                )

        # 5. Seed Demonstration Complaints (4 required cases)
        complaints_data = [
            (
                "CMP-2026-001",
                bk1,
                alice,
                "Broken Equipment",
                "During our 3-hour client presentation, the ceiling-mounted projector would not turn on or output any video signal. We contacted front desk staff but no replacement was available. We could not conduct our presentation properly.",
                "Partial Refund",
                "UNDER REVIEW",
                "sample_images/projector_broken.png",
                "projector_broken.png",
                "RELEVANT",
                {
                    "image_description": "Ceiling-mounted multimedia projector in Meeting Room A with status power LED unlit.",
                    "complaint_category": "Broken Equipment",
                    "validation_status": "RELEVANT",
                    "explanation": "The image shows the ceiling projector referenced in the complaint. However, a static photo cannot conclusively prove that electrical signal failed during the booking duration.",
                    "visible_evidence": ["Meeting room projector mounted on ceiling", "No display output active on projector lens"],
                    "missing_evidence": ["Audio-visual technician diagnostic log", "HDMI cable integrity test"],
                    "limitations": ["Static image confirms presence and physical mounting but cannot confirm live signal feed."],
                    "confidence_score": 0.88,
                    "is_demo": True,
                },
                "The meeting room was cleaned in the morning. The guest did not alert building maintenance until 45 minutes into their session.",
                {
                    "summary": "Customer reported projector malfunction in Meeting Room A during a 3-hour booking.",
                    "identified_issues": ["Projector failure", "Disrupted client meeting", "Host notification delay of 45 mins"],
                    "verified_facts": [
                        "Meeting Room A booking reference BK-2026-1001 exists for Alice Johnson on 2026-10-22 (10:00 - 13:00).",
                        "Projector is advertised as a primary amenity for Meeting Room A.",
                        "Total booking amount was ₹1,500.00.",
                    ],
                    "customer_allegations": [
                        "Customer alleges the projector did not turn on or output video for the client presentation.",
                        "Customer alleges front desk could not provide a replacement.",
                    ],
                    "owner_allegations": [
                        "Host claims room was inspected in morning and customer did not report issue until 45 minutes elapsed.",
                    ],
                    "unknown_information": [
                        "Exact cause of projector malfunction (bulb life vs HDMI cable).",
                        "Whether backup portable display was offered.",
                    ],
                    "supporting_evidence": ["Photograph of ceiling-mounted projector in Meeting Room A."],
                    "contradicting_evidence": [],
                    "missing_evidence": ["Technician service ticket or on-site inspection timestamp."],
                    "policy_references": [
                        "Amenity Malfunction Policy Section 4.1: If primary equipment in a Meeting Room is non-functional upon check-in and cannot be repaired within 30 minutes, customer is entitled to a 50% partial refund.",
                    ],
                    "ai_explanation": "Projector is an advertised primary amenity for Meeting Room A. While host states the report occurred at 45 minutes, host acknowledged no replacement was made available during the 3-hour reservation. Amenity Malfunction Policy Section 4.1 specifies a 50% partial refund of the booking amount (₹750.00).",
                    "proposed_resolution": "PARTIAL_REFUND",
                    "suggested_refund_percentage": 50.0,
                    "suggested_refund_amount": 750.0,
                    "requires_manual_review": False,
                    "uncertainty_level": "LOW",
                    "is_demo": True,
                },
            ),
            (
                "CMP-2026-002",
                bk2,
                bob,
                "Access Denied",
                "I arrived at the building at 1:55 PM for my 2:00 PM booking. The smart keypad lock was malfunctioning and the PIN code provided in the booking confirmation was rejected. Nobody was at the reception desk to assist me.",
                "Full Refund",
                "UNDER REVIEW",
                "sample_images/locked_cabin_door.png",
                "locked_cabin_door.png",
                "RELEVANT",
                {
                    "image_description": "Digital keypad lock on Executive Cabin 101 displaying 'Access Denied' red alert message.",
                    "complaint_category": "Access Denied",
                    "validation_status": "RELEVANT",
                    "explanation": "The image directly shows the cabin entry smart lock indicating an access denial warning at the doorway.",
                    "visible_evidence": ["Electronic smart door lock with red error indicator", "Executive Cabin 101 door plaque"],
                    "missing_evidence": ["Server-side electronic lock audit trail"],
                    "limitations": ["Photo shows keypad error at one point in time; does not reveal whether SMS update was received."],
                    "confidence_score": 0.92,
                    "is_demo": True,
                },
                "The door PIN code was reset at noon. We sent an updated code via SMS, but customer says they did not receive it.",
                {
                    "summary": "Customer unable to gain entry to Executive Cabin 101 due to updated door code not received.",
                    "identified_issues": ["Lockout at entrance", "Host updated code without ensuring customer delivery"],
                    "verified_facts": [
                        "Booking BK-2026-1002 for Executive Cabin 101 confirmed for Bob Smith on 2026-10-23.",
                        "Total booking amount was ₹2,400.00.",
                        "Smart lock access is listed as a primary feature of Executive Cabin 101.",
                    ],
                    "customer_allegations": [
                        "Customer entered provided PIN and was locked out; front desk was vacant.",
                    ],
                    "owner_allegations": [
                        "Owner admits door PIN code was reset at noon and updated code may not have reached the customer.",
                    ],
                    "unknown_information": [
                        "Telecommunications carrier delivery status of the SMS message.",
                    ],
                    "supporting_evidence": [
                        "Photo of electronic keypad error on Executive Cabin door.",
                        "Owner admission of changing PIN code at noon.",
                    ],
                    "contradicting_evidence": [],
                    "missing_evidence": ["Access control gateway log."],
                    "policy_references": [
                        "Space Access Policy Section 2.1: Full denial of access due to host code reset or absence entitles customer to 100% full refund.",
                    ],
                    "ai_explanation": "Host confirms that door PIN was modified prior to check-in and access was not established within 20 minutes. Under Space Access Policy Section 2.1, guest is entitled to a 100% Full Refund of ₹2,400.00.",
                    "proposed_resolution": "FULL_REFUND",
                    "suggested_refund_percentage": 100.0,
                    "suggested_refund_amount": 2400.0,
                    "requires_manual_review": False,
                    "uncertainty_level": "LOW",
                    "is_demo": True,
                },
            ),
            (
                "CMP-2026-003",
                bk3,
                charlie,
                "Wi-Fi Problem",
                "The Wi-Fi was completely down for the entire afternoon. I was unable to join zoom calls or finish my client deliverables.",
                "Partial Refund",
                "AWAITING EVIDENCE",
                "sample_images/garbage_bin_mismatch.png",
                "garbage_bin_mismatch.png",
                "UNRELATED",
                {
                    "image_description": "A plastic garbage bin containing discarded disposable cups and paper in a building corridor.",
                    "complaint_category": "Wi-Fi Problem",
                    "validation_status": "UNRELATED",
                    "explanation": "Image Mismatch Detected: The uploaded image appears to show a garbage bin. It may not provide evidence for the reported Wi-Fi issue. Please upload a relevant photograph (such as router hardware, connection error screenshot, or speed test), or continue without an image.",
                    "visible_evidence": ["Plastic garbage bin", "Discarded paper and beverage cups"],
                    "missing_evidence": ["Network status screenshot", "Speed test result", "Router error lights"],
                    "limitations": ["The photograph depicts waste disposal and has no visible relationship to digital networking."],
                    "confidence_score": 0.95,
                    "is_demo": True,
                },
                "Building Wi-Fi operated normally all day; our ISP logs show 99.8% uptime.",
                {
                    "summary": "Customer claims total Wi-Fi outage during Day Pass booking. Uploaded photo is unrelated garbage bin.",
                    "identified_issues": ["Reported Wi-Fi outage", "Uploaded image mismatch (refuse bin)"],
                    "verified_facts": [
                        "Booking BK-2026-1003 for Open Hot Desk Day Pass on 2026-10-24 for ₹400.00.",
                        "High-speed Wi-Fi is an advertised amenity.",
                    ],
                    "customer_allegations": [
                        "Customer alleges Wi-Fi was down for entire afternoon preventing Zoom calls.",
                    ],
                    "owner_allegations": [
                        "Host claims building network maintained 99.8% uptime.",
                    ],
                    "unknown_information": [
                        "Whether customer had client-side device issues or network DHCP pool exhaustion.",
                    ],
                    "supporting_evidence": [],
                    "contradicting_evidence": ["Uploaded evidence shows unrelated garbage bin."],
                    "missing_evidence": ["Network speed test, screenshot of connection failure, or ISP outage report."],
                    "policy_references": [
                        "Amenity Malfunction Policy Section 3.2 & 3.3: Image mismatch requires customer to submit network diagnostics or host confirmation; otherwise manual review is required.",
                    ],
                    "ai_explanation": "The uploaded photograph is unrelated to the Wi-Fi claim. The host asserts network uptime was 99.8%. Under Amenity Malfunction Policy Section 3.3, unresolved conflicting claims without technical verification require manual investigation or submission of proper diagnostic evidence.",
                    "proposed_resolution": "MANUAL_INVESTIGATION",
                    "suggested_refund_percentage": 0.0,
                    "suggested_refund_amount": 0.0,
                    "requires_manual_review": True,
                    "uncertainty_level": "HIGH",
                    "is_demo": True,
                },
            ),
            (
                "CMP-2026-004",
                bk4,
                alice,
                "Property Damage",
                "The host is accusing me of cracking the armrest of the office chair at desk #12. The chair armrest was already cracked and taped when I sat down at 9:00 AM.",
                "Other",
                "MANUAL INVESTIGATION",
                "sample_images/damaged_chair.png",
                "damaged_chair.png",
                "PARTIALLY_RELEVANT",
                {
                    "image_description": "Ergonomic black mesh office chair showing cracked right armrest assembly with duct tape residue.",
                    "complaint_category": "Property Damage",
                    "validation_status": "PARTIALLY_RELEVANT",
                    "explanation": "The image establishes that the chair armrest is cracked, but cannot determine whether the fracture occurred prior to or during the customer's occupancy.",
                    "visible_evidence": ["Office chair armrest crack", "Adhesive residue"],
                    "missing_evidence": ["Pre-check-in inspection photograph", "CCTV coverage of workspace area"],
                    "limitations": ["A static photo of damage cannot establish timestamp of causation."],
                    "confidence_score": 0.85,
                    "is_demo": True,
                },
                "The chair was brand new last week. The customer leaned back forcefully and snapped the armrest support.",
                {
                    "summary": "Host claims customer snapped chair armrest; customer states chair was already damaged upon arrival.",
                    "identified_issues": ["Property damage dispute", "Conflicting accounts of when damage occurred"],
                    "verified_facts": [
                        "Booking BK-2026-1004 for Dedicated Quiet Desk #12 on 2026-10-18 was completed.",
                        "Chair armrest is cracked and shows adhesive residue.",
                    ],
                    "customer_allegations": [
                        "Customer asserts chair was already cracked and taped at 9:00 AM arrival.",
                    ],
                    "owner_allegations": [
                        "Host asserts chair was new and customer caused damage by excessive force.",
                    ],
                    "unknown_information": [
                        "Exact physical condition of chair immediately prior to 9:00 AM check-in.",
                        "Who applied the adhesive tape residue visible in the photograph.",
                    ],
                    "supporting_evidence": ["Photo showing cracked armrest and aged adhesive residue."],
                    "contradicting_evidence": [
                        "Presence of adhesive tape residue contradicts host's claim that chair was brand new and unbroken before check-in.",
                    ],
                    "missing_evidence": ["Contemporaneous pre-booking inspection checklist or photos."],
                    "policy_references": [
                        "Property Damage Policy Section 1.1 & 1.2: Host must provide pre-check-in photos; conflicting allegations without pre-inspection require Manual Investigation.",
                    ],
                    "ai_explanation": "Adhesive residue on the armrest strongly suggests pre-existing damage, contradicting the host's assertion that the chair was pristine. However, since contemporaneous check-in inspection records are absent, Property Damage Policy Section 1.2 mandates referral to Manual Investigation for human adjudication.",
                    "proposed_resolution": "MANUAL_INVESTIGATION",
                    "suggested_refund_percentage": 0.0,
                    "suggested_refund_amount": 0.0,
                    "requires_manual_review": True,
                    "uncertainty_level": "HIGH",
                    "is_demo": True,
                },
            ),
        ]

        for (
            ref,
            b_id,
            c_id,
            cat,
            desc,
            exp_res,
            st,
            ev_path,
            ev_orig_name,
            val_st,
            val_res,
            owner_stmt,
            ai_inv,
        ) in complaints_data:
            existing_cmp = cursor.execute("SELECT id FROM COMPLAINTS WHERE complaint_reference = ?", (ref,)).fetchone()
            if not existing_cmp:
                cursor.execute(
                    """INSERT INTO COMPLAINTS 
                    (complaint_reference, booking_id, customer_id, category, description, expected_resolution, status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (ref, b_id, c_id, cat, desc, exp_res, st),
                )
                cmp_id = cursor.lastrowid
                print(f"Created complaint: {ref} (id: {cmp_id})")

                # Insert Evidence
                cursor.execute(
                    """INSERT INTO EVIDENCE 
                    (complaint_id, file_path, original_filename, validation_status, validation_result) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (cmp_id, ev_path, ev_orig_name, val_st, json.dumps(val_res)),
                )

                # Insert Owner Statement
                cursor.execute(
                    "INSERT INTO OWNER_STATEMENTS (complaint_id, statement) VALUES (?, ?)",
                    (cmp_id, owner_stmt),
                )

                # Insert AI Investigation
                cursor.execute(
                    """INSERT INTO AI_INVESTIGATIONS 
                    (complaint_id, verified_facts_json, customer_allegations_json, owner_allegations_json, 
                     unknown_information_json, evidence_analysis_json, policy_references_json, 
                     proposed_resolution, explanation, requires_manual_review) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        cmp_id,
                        json.dumps(ai_inv["verified_facts"]),
                        json.dumps(ai_inv["customer_allegations"]),
                        json.dumps(ai_inv["owner_allegations"]),
                        json.dumps(ai_inv["unknown_information"]),
                        json.dumps(ai_inv["supporting_evidence"]),
                        json.dumps(ai_inv["policy_references"]),
                        ai_inv["proposed_resolution"],
                        ai_inv["ai_explanation"],
                        1 if ai_inv["requires_manual_review"] else 0,
                    ),
                )

    print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
