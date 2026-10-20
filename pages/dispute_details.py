"""
Admin Complaint Investigation Page.
Presents all 6 investigation sections on one consolidated page:
Section 1: Booking Details
Section 2: Customer Complaint
Section 3: Uploaded Evidence (with mismatch warning and image inspection)
Section 4: Space Owner Statement
Section 5: AI Dispute Investigation (distinguishing Facts, Allegations, Unknowns, Policy Citations)
Section 6: Admin Decision (Human-in-the-loop controls, approval/rejection/modification and persistence)
"""

from pathlib import Path
from datetime import datetime
import streamlit as st
from database.db import fetch_one, execute_insert, execute_query
from services.complaint_service import get_complaint_details
from services.investigation_service import generate_dispute_investigation
from components.navigation import navigate_to, check_page_authorization
from components.styles import get_status_badge_html

BASE_DIR = Path(__file__).resolve().parent.parent


def save_admin_decision(
    complaint_id: int,
    admin_id: int,
    proposed_res: str,
    action: str,
    final_res: str,
    reason: str,
    final_amount: float,
) -> bool:
    """Save admin's final decision in SQLite and transition complaint status."""
    # Determine new status based on action
    if action == "Approve AI Recommendation":
        new_status = "RESOLVED"
    elif action == "Reject AI Recommendation":
        new_status = "CLOSED"
    elif action == "Modify Decision":
        new_status = "RESOLVED"
    elif action == "Request Additional Evidence":
        new_status = "AWAITING EVIDENCE"
    elif action == "Send for Manual Investigation":
        new_status = "MANUAL INVESTIGATION"
    else:
        new_status = "UNDER REVIEW"

    try:
        # Check if decision exists
        existing = fetch_one("SELECT id FROM ADMIN_DECISIONS WHERE complaint_id = ?", (complaint_id,))
        if existing:
            execute_query(
                """UPDATE ADMIN_DECISIONS 
                SET admin_id = ?, proposed_resolution = ?, final_resolution = ?, action = ?, reason = ?, final_amount = ?, created_at = CURRENT_TIMESTAMP
                WHERE complaint_id = ?""",
                (admin_id, proposed_res, final_res, action, reason, final_amount, complaint_id),
            )
        else:
            execute_insert(
                """INSERT INTO ADMIN_DECISIONS 
                (complaint_id, admin_id, proposed_resolution, final_resolution, action, reason, final_amount) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (complaint_id, admin_id, proposed_res, final_res, action, reason, final_amount),
            )

        # Update complaint status
        execute_query("UPDATE COMPLAINTS SET status = ? WHERE id = ?", (new_status, complaint_id))

        # Record audit log
        execute_insert(
            "INSERT INTO AUDIT_LOGS (user_id, action, entity_type, entity_id) VALUES (?, ?, 'COMPLAINT_DECISION', ?)",
            (admin_id, f"Admin decided: {action} ({final_res})", complaint_id),
        )

        return True
    except Exception as e:
        print(f"Error saving decision: {e}")
        return False


def render_dispute_details():
    """Render the comprehensive investigation dashboard for the administrator."""
    if not check_page_authorization("ADMIN"):
        return

    admin = st.session_state["user"]
    complaint_id = st.session_state.get("selected_complaint_id")

    if not complaint_id:
        st.error("No complaint selected.")
        navigate_to("admin_dashboard")
        return

    cmp = get_complaint_details(complaint_id)
    if not cmp:
        st.error("Complaint not found.")
        navigate_to("admin_dashboard")
        return

    # Back button
    col_nav, col_r = st.columns([1, 4])
    with col_nav:
        if st.button("← Back to Dashboard", key="btn_admin_back_to_list"):
            navigate_to("admin_dashboard")

    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h1>Dispute Adjudication: {cmp['complaint_reference']}</h1>
            <p style="color: #64748B;">
                Case status: {get_status_badge_html(cmp['status'])} &nbsp;|&nbsp;
                Customer: <strong>{cmp['customer_name']}</strong> ({cmp['customer_email']}) &nbsp;|&nbsp;
                Space: <strong>{cmp['space_name']}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ==========================================================
    # SECTION 1: BOOKING DETAILS
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 1: BOOKING DETAILS")
    col1_1, col1_2, col1_3 = st.columns(3)

    with col1_1:
        st.markdown(f"**Booking ID / Reference:** `#{cmp['booking_id']} ({cmp['booking_reference']})`")
        st.markdown(f"**Customer Name:** {cmp['customer_name']}")
        st.markdown(f"**Space Name:** {cmp['space_name']} ({cmp['space_category']})")

    with col1_2:
        st.markdown(f"**Booking Date:** {cmp['booking_date']}")
        st.markdown(f"**Time Window:** {cmp['start_time']} to {cmp['end_time']}")
        st.markdown(f"**Location:** {cmp['space_location']}")

    with col1_3:
        st.markdown(f"**Booking Amount Paid:** <strong style='color:#1E3A8A; font-size:1.1rem;'>₹{cmp['booking_amount']:,.2f}</strong>", unsafe_allow_html=True)
        amenities = cmp.get("amenities_list", [])
        st.markdown(f"**Advertised Amenities:** {', '.join(amenities) if amenities else 'Standard'}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # SECTION 2: CUSTOMER COMPLAINT
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 2: CUSTOMER COMPLAINT")
    col2_1, col2_2 = st.columns([2, 1])

    with col2_1:
        st.markdown(f"**Complaint Category:** <span class='badge badge-under-review'>{cmp['category']}</span>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:#F8FAFC; border-left:4px solid #3B82F6; padding:0.9rem; margin-top:0.5rem; border-radius:4px;">
                <p style="margin:0; font-size:1rem; color:#1E293B;">"{cmp['description']}"</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2_2:
        st.markdown(f"**Customer Expected Resolution:** **{cmp['expected_resolution']}**")
        st.markdown(f"**Submission Timestamp:** {cmp['created_at']}")
        st.markdown(f"**Current Status:** {get_status_badge_html(cmp['status'])}", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # SECTION 3: UPLOADED EVIDENCE
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 3: UPLOADED EVIDENCE")

    evidence_list = cmp.get("evidence_list", [])
    if evidence_list:
        for ev in evidence_list:
            col_img, col_val = st.columns([1, 1.8])

            with col_img:
                ev_path = BASE_DIR / ev["file_path"]
                if ev_path.exists():
                    st.image(str(ev_path), caption=f"File: {ev['original_filename']}", width="stretch")
                else:
                    st.warning("Evidence image not stored on server.")

            with col_val:
                st.markdown(f"**Validation Status:** {get_status_badge_html(ev['validation_status'])}", unsafe_allow_html=True)

                parsed = ev.get("parsed_result") or {}
                if parsed.get("is_demo"):
                    st.markdown("<span class='demo-pill'>DEMO SIMULATED ANALYSIS</span>", unsafe_allow_html=True)

                if ev["validation_status"] == "UNRELATED":
                    st.markdown(
                        f"""
                        <div class="mismatch-alert" style="background:#FEF2F2; border:1px solid #FCA5A5; border-radius:8px; padding:1rem; margin-top:0.5rem; margin-bottom:0.8rem;">
                            <h5 style="margin:0 0 0.3rem 0; color:#991B1B;">⚠️ Evidence Mismatch / Invalid Image Detected</h5>
                            <p style="margin:0.2rem 0; color:#1E293B;"><strong>AI Visual Inspection:</strong> {parsed.get('image_description', 'N/A')}</p>
                            <p style="margin:0.2rem 0; color:#7F1D1D;"><strong>Policy Assessment:</strong> {parsed.get('explanation', 'N/A')}</p>
                            <div style="margin-top:0.6rem; padding:0.5rem 0.75rem; background:#FFF1F2; border-left:3px solid #E11D48; border-radius:4px;">
                                <strong style="color:#9F1239;">📋 Recommendation for Admin:</strong>
                                <span style="color:#881337;">{parsed.get('recommendation_for_admin') or "The uploaded photograph is not valid proof for this claim. Recommend selecting 'Request Additional Evidence' to prompt customer for a speed test screenshot, or 'Send for Manual Investigation'."}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"**AI Description:** {parsed.get('image_description', 'N/A')}")
                    st.markdown(f"**Relevance Assessment:** {parsed.get('explanation', 'N/A')}")

                vis = parsed.get("visible_evidence", [])
                if vis:
                    st.markdown(f"**Visible Elements:** {', '.join(vis)}")

                miss = parsed.get("missing_evidence", [])
                if miss:
                    st.markdown(f"**Missing Proof:** {', '.join(miss)}")

                limits = parsed.get("limitations", [])
                if limits:
                    st.markdown(f"**Photographic Limitations:** {', '.join(limits)}")

                if st.button("🔄 Re-evaluate Evidence with AI", key=f"reval_btn_{ev['id']}"):
                    from services.image_validation_service import validate_complaint_evidence
                    with st.spinner("Re-evaluating image evidence with AI..."):
                        new_val = validate_complaint_evidence(
                            image_path=str(ev_path),
                            complaint_category=cmp["category"],
                            complaint_description=cmp["description"],
                            original_filename=ev["original_filename"],
                        )
                        from services.complaint_service import add_or_replace_evidence
                        add_or_replace_evidence(
                            complaint_id=cmp["id"],
                            file_path=ev["file_path"],
                            original_filename=ev["original_filename"],
                            validation_status=new_val.validation_status.value,
                            validation_result=new_val.model_dump(mode="json"),
                        )
                        st.rerun()
    else:
        st.info("No photographic evidence was uploaded by the customer for this dispute.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # SECTION 4: SPACE OWNER STATEMENT
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 4: SPACE OWNER STATEMENT")
    owner_stmt = cmp.get("owner_statement")

    if owner_stmt:
        st.markdown(
            f"""
            <div style="background:#F1F5F9; border-left:4px solid #64748B; padding:0.9rem; border-radius:4px;">
                <p style="margin:0; font-size:1rem; color:#1E293B;">"{owner_stmt}"</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background:#FEF2F2; padding:0.75rem 1rem; border-radius:6px; color:#991B1B;">
                <em>No owner statement has been provided.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # SECTION 5: AI DISPUTE INVESTIGATION
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 5: AI DISPUTE INVESTIGATION")

    ai_inv = cmp.get("ai_investigation")

    # If no AI investigation is recorded yet, provide a one-click trigger
    if not ai_inv:
        st.info("AI dispute investigation has not been computed yet for this complaint.")
        if st.button("⚡ Run AI Dispute Investigation", key="btn_run_ai_inv"):
            with st.spinner("AI evaluating verified facts and retrieving policies..."):
                generate_dispute_investigation(cmp["id"])
                st.rerun()
    else:
        st.markdown(
            f"""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; padding:1.2rem; margin-bottom:1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="demo-pill">🤖 AI RECOMMENDATION</span>
                    <span style="font-size:0.85rem; color:#1E40AF;">Generated: {ai_inv['created_at']}</span>
                </div>
                <div style="margin-top:0.5rem; font-size:1.3rem; font-weight:700; color:#1E3A8A;">
                    Proposed Outcome: {ai_inv['proposed_resolution']}
                </div>
                <p style="margin-top:0.5rem; font-size:0.98rem; color:#1E293B; line-height:1.5;">
                    <strong>AI Adjudication Reasoning:</strong> {ai_inv['explanation']}
                </p>
                <div style="margin-top:0.5rem;">
                    {"<span class='badge badge-manual-investigation'>⚠️ REQUIRES MANUAL REVIEW</span>" if ai_inv.get('requires_manual_review') else "<span class='badge badge-confirmed'>✅ HIGH CONFIDENCE</span>"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 4 Categorized Columns: Verified Facts, Customer Allegations, Owner Allegations, Unknown Info
        col_f, col_c, col_o, col_u = st.columns(4)

        with col_f:
            st.markdown("#### 1. Verified Facts")
            facts = ai_inv.get("verified_facts", [])
            if facts:
                for f in facts:
                    st.markdown(f"• {f}")
            else:
                st.markdown("• Booking details in SQLite database")

        with col_c:
            st.markdown("#### 2. Customer Allegations")
            callegs = ai_inv.get("customer_allegations", [])
            if callegs:
                for c in callegs:
                    st.markdown(f"• {c}")
            else:
                st.markdown(f"• {cmp['description']}")

        with col_o:
            st.markdown("#### 3. Owner Allegations")
            oallegs = ai_inv.get("owner_allegations", [])
            if oallegs:
                for o in oallegs:
                    st.markdown(f"• {o}")
            else:
                st.markdown(f"• {owner_stmt or 'No statement provided'}")

        with col_u:
            st.markdown("#### 4. Unknown Info")
            unknowns = ai_inv.get("unknown_information", [])
            if unknowns:
                for u in unknowns:
                    st.markdown(f"• {u}")
            else:
                st.markdown("• On-site equipment diagnostic status")

        st.markdown("<hr style='margin:1rem 0; border:none; border-top:1px solid #E2E8F0;'/>", unsafe_allow_html=True)

        # Retrieved Policy Citations
        with st.expander("📚 Retrieved Knowledge Base Policies (Source of Truth)"):
            policies = ai_inv.get("policy_references", [])
            if policies:
                for p in policies:
                    st.markdown(f"📌 **{p}**")
            else:
                st.info("No specific policy clauses were indexed for this category.")

        if st.button("🔄 Re-run AI Dispute Investigation", key="btn_rerun_ai_inv"):
            with st.spinner("AI re-evaluating dispute facts and policy guidelines..."):
                generate_dispute_investigation(cmp["id"])
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================================
    # SECTION 6: ADMIN DECISION
    # ==========================================================
    st.markdown('<div class="ui-card">', unsafe_allow_html=True)
    st.markdown("### SECTION 6: ADMIN DECISION & ADJUDICATION")
    st.markdown(
        "<p style='color:#64748B; font-size:0.9rem;'>The AI recommendation is advisory. Human administrators hold final adjudicative authority.</p>",
        unsafe_allow_html=True,
    )

    existing_dec = cmp.get("admin_decision")
    if existing_dec:
        st.markdown(
            f"""
            <div style="background:#F0FDF4; border:1px solid #86EFAC; border-radius:8px; padding:1rem; margin-bottom:1.2rem;">
                <h4 style="color:#166534; margin:0 0 0.3rem 0;">✅ Recorded Final Decision</h4>
                <p style="margin:0.2rem 0;"><strong>Action:</strong> {existing_dec['action']}</p>
                <p style="margin:0.2rem 0;"><strong>Final Resolution:</strong> {existing_dec['final_resolution']}</p>
                <p style="margin:0.2rem 0;"><strong>Final Amount Approved:</strong> ₹{existing_dec['final_amount']:,.2f}</p>
                <p style="margin:0.2rem 0;"><strong>Admin Reason:</strong> {existing_dec['reason']}</p>
                <p style="margin:0.2rem 0; font-size:0.8rem; color:#64748B;">Recorded by {existing_dec['admin_name']} on {existing_dec['created_at']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Decision Form
    with st.form("admin_decision_form"):
        col_act, col_res, col_amt = st.columns([1.5, 1.5, 1])

        with col_act:
            reason_placeholder = (
                f"Customer submitted an invalid/mismatched image for {cmp['category']}. In accordance with marketplace policy, requesting technical proof (e.g. speed test screenshot or router log) before final settlement."
                if any(ev.get("validation_status") == "UNRELATED" for ev in evidence_list)
                else "Explain why this decision was reached based on evidence and policies..."
            )

            has_unrelated_evidence = any(ev.get("validation_status") == "UNRELATED" for ev in evidence_list)
            action_options = [
                "Approve AI Recommendation",
                "Reject AI Recommendation",
                "Modify Decision",
                "Request Additional Evidence",
                "Send for Manual Investigation",
            ]
            default_act_idx = 3 if has_unrelated_evidence else 0

            action_choice = st.selectbox(
                "Select Admin Action",
                options=action_options,
                index=default_act_idx,
                key="admin_action_select",
            )

        with col_res:
            res_options = ["FULL_REFUND", "PARTIAL_REFUND", "NO_REFUND", "MANUAL_INVESTIGATION"]
            default_res_idx = 0
            if ai_inv and ai_inv.get("proposed_resolution") in res_options:
                default_res_idx = res_options.index(ai_inv["proposed_resolution"])

            final_res_choice = st.selectbox(
                "Final Resolution",
                options=res_options,
                index=default_res_idx,
                key="admin_final_res_select",
            )

        with col_amt:
            # Default amount to booking amount or 50% depending on resolution
            default_amt = 0.0
            if final_res_choice == "FULL_REFUND":
                default_amt = float(cmp["booking_amount"])
            elif final_res_choice == "PARTIAL_REFUND":
                default_amt = round(float(cmp["booking_amount"]) * 0.5, 2)

            final_approved_amount = st.number_input(
                "Final Settlement Amount (₹)",
                min_value=0.0,
                max_value=float(cmp["booking_amount"]),
                value=default_amt,
                step=50.0,
                key="admin_final_amount_input",
            )

        reason_text = st.text_area(
            "Adjudication Reason & Policy Justification",
            placeholder=reason_placeholder,
            height=90,
            key="admin_reason_input",
        )

        submit_decision = st.form_submit_button("Submit Final Decision", width="stretch")

        if submit_decision:
            if not reason_text.strip():
                st.error("Please enter a decision reason to document this administrative action.")
            else:
                prop_res = ai_inv["proposed_resolution"] if ai_inv else "PENDING"
                ok = save_admin_decision(
                    complaint_id=cmp["id"],
                    admin_id=admin["id"],
                    proposed_res=prop_res,
                    action=action_choice,
                    final_res=final_res_choice,
                    reason=reason_text.strip(),
                    final_amount=float(final_approved_amount),
                )
                if ok:
                    st.success("Decision recorded successfully! Status updated.")
                    st.rerun()
                else:
                    st.error("Failed to save decision in database.")

    st.markdown("</div>", unsafe_allow_html=True)
