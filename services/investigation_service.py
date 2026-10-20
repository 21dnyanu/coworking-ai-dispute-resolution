"""
AI Dispute Investigation Service.
Integrates LangChain, FAISS policy retrieval, and Google Gemini to produce
structured, evidence-based dispute assessments distinguishing verified facts,
customer allegations, owner allegations, and unknown information.
"""

import json
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from models.schemas import DisputeInvestigationOutput, ProposedResolution
from database.db import fetch_one, execute_insert, execute_query
from services.policy_service import retrieve_relevant_policies
from services.gemini_service import is_live_api_configured, get_active_api_key

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()


def get_demo_dispute_investigation(
    complaint: dict,
    policies: List[dict],
) -> DisputeInvestigationOutput:
    """
    Generate realistic, policy-grounded dispute investigations in DEMO MODE.
    Examines case specifics and distinguishes facts, allegations, unknown variables,
    and inspects uploaded evidence validity.
    """
    cat = (complaint.get("category") or "").lower()
    desc = (complaint.get("description") or "").lower()
    amount = float(complaint.get("booking_amount") or 0.0)
    space_name = complaint.get("space_name", "Coworking Space")
    space_cat = complaint.get("space_category", "Space")
    ref = complaint.get("booking_reference", "N/A")
    date_str = complaint.get("booking_date", "N/A")
    owner_stmt = complaint.get("owner_statement")

    # Extract policy citations
    policy_texts = [f"{p['title']} ({p['section']}): {p['content'][:150]}..." for p in policies]

    # Inspect uploaded evidence
    evidence_list = complaint.get("evidence_list") or []
    has_unrelated_evidence = False
    evidence_desc_str = "photographic evidence"
    evidence_orig_name = "evidence.jpg"

    for ev in evidence_list:
        vstat = ev.get("validation_status")
        parsed = ev.get("parsed_result") or {}
        evidence_orig_name = ev.get("original_filename") or "evidence.jpg"
        if vstat == "UNRELATED":
            has_unrelated_evidence = True
            evidence_desc_str = parsed.get("image_description") or "an unrelated desk or refuse photo"
            break
        elif parsed.get("image_description"):
            evidence_desc_str = parsed.get("image_description")

    # CASE C1: Wi-Fi with UNRELATED / MISMATCHED image (e.g. desk with food tray, garbage bin, furniture)
    if ("wi-fi" in cat or "wifi" in cat or "internet" in desc) and (has_unrelated_evidence or "desk" in evidence_desc_str.lower() or "tray" in evidence_desc_str.lower() or "garbage" in evidence_desc_str.lower() or "bin" in evidence_desc_str.lower()):
        admin_rec = (
            "⚠️ Evidence Mismatch Detected: The customer reported a Wi-Fi Problem, but the uploaded photograph "
            f"depicts {evidence_desc_str} rather than technical network proof (such as a speed test screenshot, "
            "router status indicator lights, or connection error dialog). In accordance with Amenity Malfunction Policy Section 3.3, "
            "do not approve automated financial compensation based on this image. "
            "RECOMMENDATION FOR ADMIN: Select 'Request Additional Evidence' to prompt the customer to re-upload a speed test screenshot "
            "or connection log, or select 'Send for Manual Investigation' to review router session logs with the host."
        )
        return DisputeInvestigationOutput(
            summary=f"Wi-Fi outage claim for {space_name} with invalid evidence (image mismatch) and conflicting host logs.",
            identified_issues=[
                "Reported Internet / Wi-Fi outage",
                f"Uploaded image mismatch ({evidence_desc_str})",
                "Absence of technical diagnostic proof (speed test / error screenshot)",
                "Contradictory host operational statement",
            ],
            verified_facts=[
                f"Customer reserved {space_name} under booking reference {ref} on {date_str}.",
                f"Booking fee paid was ₹{amount:,.2f}.",
                "High-speed Wi-Fi is an advertised primary amenity for this workspace.",
                f"Customer submitted photographic evidence ({evidence_orig_name}), which AI validation classified as UNRELATED ({evidence_desc_str}).",
            ],
            customer_allegations=[
                f"Customer alleges: '{complaint['description']}'",
                "Customer states Wi-Fi connectivity failed, disrupting normal work.",
            ],
            owner_allegations=[
                f"Host states: '{owner_stmt}'" if owner_stmt else "Host asserts building network maintained normal operation with 99.8% uptime.",
            ],
            unknown_information=[
                "Whether customer experienced local client-side Wi-Fi adapter failure, incorrect credentials, or DHCP lease exhaustion.",
                "Actual router throughput, latency, and packet loss statistics during the specific booking hours.",
            ],
            supporting_evidence=[],
            contradicting_evidence=[
                f"Uploaded photograph depicts {evidence_desc_str}, providing no valid technical evidence of network failure.",
                "Host asserts network maintained 99.8% uptime with active ISP traffic.",
            ],
            missing_evidence=[
                "Network speed test screenshot, ping/packet loss diagnostic, or verified ISP outage advisory.",
            ],
            policy_references=[
                "Amenity Malfunction Policy Section 3.2 & 3.3: Photographic evidence of unrelated furniture or refuse does not verify signal failure. Unresolved conflicting claims without diagnostic proof mandate referral to Manual Investigation or Request for Additional Evidence.",
            ] + policy_texts[:1],
            ai_explanation=(
                f"The customer reported a Wi-Fi connectivity issue ('{complaint['description']}'), but the uploaded photograph ({evidence_desc_str}) "
                "is an image mismatch that does not substantiate the claim. The space owner reports normal network operations with 99.8% uptime. "
                "Under Amenity Malfunction Policy Section 3.3, claims with evidence mismatch cannot be approved for automated financial refund.\n\n"
                f"{admin_rec}"
            ),
            proposed_resolution=ProposedResolution.MANUAL_INVESTIGATION,
            suggested_refund_percentage=0.0,
            suggested_refund_amount=0.0,
            requires_manual_review=True,
            uncertainty_level="HIGH",
            recommendation_for_admin=admin_rec,
            is_demo=True,
        )

    # CASE A: Projector / AV Equipment Breakdown
    if "projector" in desc or "equipment" in cat:
        refund_pct = 50.0
        refund_amt = round(amount * (refund_pct / 100.0), 2)
        admin_rec = (
            f"The projector is a verified primary amenity advertised for {space_name}. While the host states notification was delayed, "
            f"no operational replacement was provided during the booking window. Recommend approving a 50% partial refund of ₹{refund_amt:,.2f} "
            "in accordance with Amenity Malfunction Policy Section 4.1."
        )
        return DisputeInvestigationOutput(
            summary=f"Dispute regarding inoperable projector in {space_name} during booking {ref}.",
            identified_issues=["Projector failure upon check-in", "Client presentation disrupted", "No replacement provided"],
            verified_facts=[
                f"Booking {ref} exists for {space_name} ({space_cat}) on {date_str}.",
                f"Total booking fee paid was ₹{amount:,.2f}.",
                "Projector is explicitly advertised as an included primary amenity for this meeting space.",
            ],
            customer_allegations=[
                "Customer states that the ceiling-mounted projector would not power on or output video.",
                "Customer states that on-site front desk staff was unable to provide a functional replacement.",
            ],
            owner_allegations=[
                f"Host states: '{owner_stmt}'" if owner_stmt else "Host claims the room was cleaned and ready.",
            ],
            unknown_information=[
                "Whether the projector bulb failure was intermittent or electrical cable fault.",
                "Exact timestamp when customer first notified reception staff.",
            ],
            supporting_evidence=[
                "Customer submitted photo of ceiling projector with unlit indicator LED.",
                "Advertised amenities list verifying projector inclusion.",
            ],
            contradicting_evidence=[],
            missing_evidence=[
                "Facility technician diagnostic work order or electrical check log.",
            ],
            policy_references=[
                "Amenity Malfunction Policy Section 4.1: If primary equipment in a Meeting Room is non-functional upon check-in and cannot be repaired within 30 minutes, the customer is entitled to a 50% partial refund.",
            ] + policy_texts[:1],
            ai_explanation=(
                f"The projector is a verified primary amenity advertised for {space_name}. While the host states "
                "notification was delayed, no operational replacement was provided during the booking window. "
                f"In accordance with Amenity Malfunction Policy Section 4.1, a 50% partial refund of ₹{refund_amt:,.2f} is recommended."
            ),
            proposed_resolution=ProposedResolution.PARTIAL_REFUND,
            suggested_refund_percentage=refund_pct,
            suggested_refund_amount=refund_amt,
            requires_manual_review=False,
            uncertainty_level="LOW",
            recommendation_for_admin=admin_rec,
            is_demo=True,
        )

    # CASE B: Lockout / Denied Access
    if "access" in cat or "lock" in desc or "pin" in desc or "denied" in cat:
        refund_pct = 100.0
        refund_amt = amount
        admin_rec = (
            f"Customer was denied access to {space_name} due to digital door lock PIN update. "
            f"Under Space Access Policy Section 2.1, recommend approving a 100% full refund of ₹{refund_amt:,.2f}."
        )
        return DisputeInvestigationOutput(
            summary=f"Dispute regarding total denial of entry for {space_name} due to smart lock failure.",
            identified_issues=["Customer locked out at door", "Door PIN code rejected", "No front desk personnel present"],
            verified_facts=[
                f"Confirmed booking {ref} for {space_name} on {date_str}.",
                f"Total booking fee paid was ₹{amount:,.2f}.",
                "Smart Lock digital access is a verified feature of this private cabin.",
            ],
            customer_allegations=[
                "Customer states they arrived on time and the digital keypad rejected the confirmation PIN code.",
                "Customer states reception desk was vacant and no access was provided within 20 minutes.",
            ],
            owner_allegations=[
                f"Host states: '{owner_stmt}'" if owner_stmt else "Host states PIN was updated prior to booking.",
            ],
            unknown_information=[
                "Carrier SMS delivery report regarding when the updated PIN was dispatched and delivered.",
            ],
            supporting_evidence=[
                "Customer photograph of digital lock keypad showing locked alert indicator.",
                "Host statement confirming door PIN was changed at noon.",
            ],
            contradicting_evidence=[],
            missing_evidence=["Cloud electronic lock gateway timestamp log."],
            policy_references=[
                "Space Access and Entry Lockout Policy Section 2.1: Full denial of access due to host code reset or absence entitles customer to 100% FULL REFUND.",
            ] + policy_texts[:1],
            ai_explanation=(
                "The host acknowledges changing the digital door code prior to check-in, and the customer was unable "
                f"to gain entry to the cabin. Under Space Access Policy Section 2.1, a 100% full refund of ₹{refund_amt:,.2f} is proposed."
            ),
            proposed_resolution=ProposedResolution.FULL_REFUND,
            suggested_refund_percentage=refund_pct,
            suggested_refund_amount=refund_amt,
            requires_manual_review=False,
            uncertainty_level="LOW",
            recommendation_for_admin=admin_rec,
            is_demo=True,
        )

    # CASE C2: General Wi-Fi with Router hardware / unverified
    if "wi-fi" in cat or "wifi" in cat or "internet" in desc:
        admin_rec = (
            "The customer reported Wi-Fi connectivity problems and host asserts 99.8% uptime. "
            "A static photograph of router hardware confirms presence but cannot prove wireless throughput loss. "
            "Recommend requesting a speed test screenshot from customer or checking host router session logs before deciding."
        )
        return DisputeInvestigationOutput(
            summary=f"Wi-Fi outage claim for {space_name} requiring technical verification.",
            identified_issues=["Reported Internet outage", "Conflicting network uptime statements", "Missing bandwidth diagnostics"],
            verified_facts=[
                f"Customer reserved {space_name} under booking reference {ref}.",
                f"Booking amount was ₹{amount:,.2f}.",
                "High-speed Wi-Fi is an advertised amenity.",
            ],
            customer_allegations=[
                "Customer alleges Wi-Fi was completely down for the afternoon, disrupting work.",
            ],
            owner_allegations=[
                f"Host states: '{owner_stmt}'" if owner_stmt else "Host asserts network maintained 99.8% uptime.",
            ],
            unknown_information=[
                "Whether customer experienced client device wireless adapter failure or DHCP lease timeout.",
                "True router throughput and packet loss statistics during the specific booking hours.",
            ],
            supporting_evidence=["Photo confirms physical presence of router hardware."] if evidence_list else [],
            contradicting_evidence=[
                "Host states network uptime was 99.8% with normal ISP traffic.",
            ],
            missing_evidence=[
                "Network speed test screenshot, error log, or verified ISP outage notice.",
            ],
            policy_references=[
                "Amenity Malfunction Policy Section 3.2: Static photograph of hardware cannot verify signal loss; technical diagnostics required. Refer to Manual Investigation.",
            ] + policy_texts[:1],
            ai_explanation=(
                "The customer reported an Internet outage while the host asserts normal network operation. "
                "Because allegations conflict and diagnostic proof is missing, Amenity Malfunction Policy Section 3.2 "
                "requires escalating this dispute to Manual Investigation or Requesting Additional Evidence."
            ),
            proposed_resolution=ProposedResolution.MANUAL_INVESTIGATION,
            suggested_refund_percentage=0.0,
            suggested_refund_amount=0.0,
            requires_manual_review=True,
            uncertainty_level="HIGH",
            recommendation_for_admin=admin_rec,
            is_demo=True,
        )

    # CASE D: Property Damage Dispute / General Case
    admin_rec = (
        "Both parties present conflicting statements regarding causation of damage. "
        "Under Property Damage Policy Section 1.2, in the absence of pre-inspection records, no automated fault or charge can be assigned. "
        "Referral to Manual Investigation is strictly required."
    )
    return DisputeInvestigationOutput(
        summary=f"Dispute regarding property damage or contested conditions at {space_name}.",
        identified_issues=["Conflicting statements regarding causation of damage", "Absence of pre-check-in condition checklist"],
        verified_facts=[
            f"Booking {ref} for {space_name} on {date_str} was completed.",
            f"Original booking charge was ₹{amount:,.2f}.",
            "Physical damage to property is documented in photographic evidence.",
        ],
        customer_allegations=[
            "Customer states the item was already damaged and taped prior to their arrival.",
        ],
        owner_allegations=[
            f"Host states: '{owner_stmt}'" if owner_stmt else "Host asserts the item was undamaged and customer caused the fracture.",
        ],
        unknown_information=[
            "Condition of the item immediately prior to customer check-in.",
            "Identity of the party who applied adhesive residue to the damaged item.",
        ],
        supporting_evidence=[
            "Photo showing aged adhesive residue, suggesting pre-existing damage prior to the booking.",
        ],
        contradicting_evidence=[
            "Presence of duct tape residue contradicts host's claim that the furniture was brand new and undamaged.",
        ],
        missing_evidence=[
            "Timestamped pre-check-in inspection photos from space management.",
        ],
        policy_references=[
            "Property Damage Policy Section 1.2: Host must provide pre-check-in photos; conflicting allegations without pre-inspection require Manual Investigation.",
        ] + policy_texts[:1],
        ai_explanation=(
            "Both parties present directly conflicting statements regarding when damage occurred. Under Property Damage "
            "Policy Section 1.2, in the absence of pre-inspection records, no automated fault or charge can be assigned. "
            "Referral to Manual Investigation is strictly required."
        ),
        proposed_resolution=ProposedResolution.MANUAL_INVESTIGATION,
        suggested_refund_percentage=0.0,
        suggested_refund_amount=0.0,
        requires_manual_review=True,
        uncertainty_level="HIGH",
        recommendation_for_admin=admin_rec,
        is_demo=True,
    )


def generate_dispute_investigation(complaint_id: int) -> DisputeInvestigationOutput:
    """
    Run full AI investigation pipeline for a complaint:
    1. Fetches booking, complaint, space, and evidence data.
    2. Retrieves top relevant policy passages using FAISS.
    3. Calls Gemini with prompt (or Demo Mode).
    4. Validates output with Pydantic.
    5. Saves investigation in SQLite AI_INVESTIGATIONS table.
    """
    from services.complaint_service import get_complaint_details

    complaint = get_complaint_details(complaint_id)
    if not complaint:
        raise ValueError(f"Complaint {complaint_id} not found.")

    # Retrieve relevant policy passages via FAISS
    query = f"{complaint['category']} {complaint['description']}"
    policy_passages = retrieve_relevant_policies(query, top_k=3)

    # Format evidence summary
    evidence_items = complaint.get("evidence_list") or []
    evidence_lines = []
    for ev in evidence_items:
        vstat = ev.get("validation_status", "UNKNOWN")
        fname = ev.get("original_filename", "photo")
        parsed = ev.get("parsed_result") or {}
        edesc = parsed.get("image_description") or "photo"
        eexp = parsed.get("explanation") or ""
        evidence_lines.append(f"- File: {fname} | Status: {vstat} | Description: {edesc} | Assessment: {eexp}")
    evidence_context = "\n".join(evidence_lines) if evidence_lines else "No photographic evidence was uploaded."

    # If Live API is configured, invoke Gemini
    if is_live_api_configured():
        try:
            import google.generativeai as genai

            active_key = get_active_api_key()
            genai.configure(api_key=active_key)
            model = genai.GenerativeModel(MODEL_NAME)

            policies_context = "\n\n".join(
                [f"DOCUMENT: {p['title']} ({p['section']})\n{p['content']}" for p in policy_passages]
            )

            prompt = f"""
You are an objective AI Dispute Adjudication Assistant for a coworking space platform.

CASE INFORMATION:
- Complaint Reference: {complaint['complaint_reference']}
- Space Name: {complaint['space_name']} ({complaint['space_category']})
- Location: {complaint['space_location']}
- Booking Amount: ₹{complaint['booking_amount']}
- Booking Date: {complaint['booking_date']} ({complaint['start_time']} - {complaint['end_time']})
- Advertised Amenities: {', '.join(complaint.get('amenities_list', []))}
- Customer Complaint Category: {complaint['category']}
- Customer Description: "{complaint['description']}"
- Customer Requested Resolution: {complaint['expected_resolution']}
- Space Owner / Host Statement: "{complaint.get('owner_statement') or 'No owner statement provided.'}"

UPLOADED EVIDENCE:
{evidence_context}

RETRIEVED POLICY PASSAGES (SOURCE OF TRUTH):
{policies_context if policies_context else "No applicable policy document was found."}

RULES:
1. Distinguish strictly:
   - VERIFIED FACTS: Information established by database records or undisputed logs.
   - CUSTOMER ALLEGATIONS: Unverified claims made by the customer.
   - OWNER ALLEGATIONS: Unverified claims made by the owner.
   - UNKNOWN INFORMATION: Critical facts that cannot be proven from available data.
2. EVIDENCE VALIDATION & MISMATCH RULE:
   If the customer uploaded evidence that is marked UNRELATED or depicts an image mismatch (e.g. food tray/desk/furniture for a Wi-Fi complaint):
   - Clearly state the image mismatch in identified_issues and contradicting_evidence.
   - Set proposed_resolution to "MANUAL_INVESTIGATION".
   - Set suggested_refund_percentage to 0.0 and suggested_refund_amount to 0.0.
   - Set requires_manual_review to true and uncertainty_level to "HIGH".
   - In recommendation_for_admin, explicitly advise the administrator to select "Request Additional Evidence" to ask for a speed test screenshot, or "Send for Manual Investigation".
3. Propose ONE of four outcomes: FULL_REFUND, PARTIAL_REFUND, NO_REFUND, or MANUAL_INVESTIGATION.
4. Calculate refund percentages strictly based on retrieved policy. Do NOT invent percentages.
5. Return ONLY a valid JSON object matching this schema:
{{
  "summary": "...",
  "identified_issues": ["..."],
  "verified_facts": ["..."],
  "customer_allegations": ["..."],
  "owner_allegations": ["..."],
  "unknown_information": ["..."],
  "supporting_evidence": ["..."],
  "contradicting_evidence": ["..."],
  "missing_evidence": ["..."],
  "policy_references": ["..."],
  "ai_explanation": "...",
  "recommendation_for_admin": "Clear guidance to administrator on next action",
  "proposed_resolution": "FULL_REFUND" | "PARTIAL_REFUND" | "NO_REFUND" | "MANUAL_INVESTIGATION",
  "suggested_refund_percentage": 50.0,
  "suggested_refund_amount": 750.0,
  "requires_manual_review": false,
  "uncertainty_level": "LOW" | "MEDIUM" | "HIGH",
  "is_demo": false
}}
"""
            resp = model.generate_content(prompt)
            clean_text = resp.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            parsed = json.loads(clean_text.strip())
            parsed["is_demo"] = False
            result = DisputeInvestigationOutput(**parsed)
        except Exception as e:
            print(f"Notice: Live Gemini call failed ({e}). Falling back to Demo Mode.")
            result = get_demo_dispute_investigation(complaint, policy_passages)
    else:
        result = get_demo_dispute_investigation(complaint, policy_passages)

    # Persist or update in AI_INVESTIGATIONS table
    existing = fetch_one("SELECT id FROM AI_INVESTIGATIONS WHERE complaint_id = ?", (complaint_id,))
    if existing:
        execute_query(
            """UPDATE AI_INVESTIGATIONS 
            SET verified_facts_json = ?, customer_allegations_json = ?, owner_allegations_json = ?,
                unknown_information_json = ?, evidence_analysis_json = ?, policy_references_json = ?,
                proposed_resolution = ?, explanation = ?, requires_manual_review = ?,
                suggested_refund_amount = ?
            WHERE complaint_id = ?""",
            (
                json.dumps(result.verified_facts),
                json.dumps(result.customer_allegations),
                json.dumps(result.owner_allegations),
                json.dumps(result.unknown_information),
                json.dumps(result.supporting_evidence),
                json.dumps(result.policy_references),
                result.proposed_resolution.value,
                result.ai_explanation,
                1 if result.requires_manual_review else 0,
                result.suggested_refund_amount,
                complaint_id,
            ),
        )
    else:
        execute_insert(
            """INSERT INTO AI_INVESTIGATIONS 
            (complaint_id, verified_facts_json, customer_allegations_json, owner_allegations_json,
             unknown_information_json, evidence_analysis_json, policy_references_json,
             proposed_resolution, explanation, requires_manual_review, suggested_refund_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                complaint_id,
                json.dumps(result.verified_facts),
                json.dumps(result.customer_allegations),
                json.dumps(result.owner_allegations),
                json.dumps(result.unknown_information),
                json.dumps(result.supporting_evidence),
                json.dumps(result.policy_references),
                result.proposed_resolution.value,
                result.ai_explanation,
                1 if result.requires_manual_review else 0,
                result.suggested_refund_amount,
            ),
        )

    return result
