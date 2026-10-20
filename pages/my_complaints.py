"""
My Complaints: status of every complaint the customer raised, plus the admin's final decision.
Allows customers to re-upload evidence when an image was flagged as mismatched or invalid.
"""

from pathlib import Path
import streamlit as st
from services.complaint_service import get_customer_complaints, get_complaint_details, add_or_replace_evidence
from services.image_validation_service import validate_and_save_uploaded_image, validate_complaint_evidence
from components.navigation import navigate_to
from components.styles import get_status_badge_html
from components.labels import resolution_label

BASE_DIR = Path(__file__).resolve().parent.parent

STATUS_HELP = {
    "SUBMITTED": "We received your complaint and it is waiting for review.",
    "UNDER REVIEW": "Our team is reviewing the booking, evidence and policies.",
    "AWAITING EVIDENCE": "Our review team requested additional evidence or a re-upload from you.",
    "MANUAL INVESTIGATION": "Your case needs a closer look by our investigation team.",
    "RESOLVED": "A final decision has been made by the administrator.",
    "CLOSED": "This complaint is closed.",
}


@st.dialog("Re-upload Evidence", width="medium")
def reupload_evidence_dialog(complaint: dict):
    st.markdown(f"### Re-upload Evidence for {complaint['complaint_reference']}")
    st.markdown(
        f"<div class='room-meta'>Category: <strong>{complaint['category']}</strong> · Space: {complaint['space_name']}</div>"
        f"<p style='color:#64748B; font-size:0.92rem; margin-top:0.4rem;'>"
        f"Please upload a screenshot or photograph directly substantiating the issue "
        f"(e.g. a network speed test screenshot showing 0 Mbps, a device connection error alert, or router status lights).</p>",
        unsafe_allow_html=True,
    )

    new_photo = st.file_uploader(
        "Choose a replacement photograph or screenshot",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"reup_file_{complaint['id']}",
    )

    if new_photo is not None:
        st.image(new_photo, caption="Selected replacement image", width=260)
        if st.button("Verify & Submit Replacement Evidence", type="primary", width="stretch", key=f"btn_save_reup_{complaint['id']}"):
            with st.spinner("AI checking and validating replacement evidence..."):
                ok, msg, dest = validate_and_save_uploaded_image(new_photo)
                if not ok:
                    st.error(msg)
                    return

                val_res = validate_complaint_evidence(
                    image_path=str(dest),
                    complaint_category=complaint["category"],
                    complaint_description=complaint["description"],
                    original_filename=new_photo.name,
                )

                success = add_or_replace_evidence(
                    complaint_id=complaint["id"],
                    file_path=str(dest),
                    original_filename=new_photo.name,
                    validation_status=val_res.validation_status.value,
                    validation_result=val_res.model_dump(mode="json"),
                )

                if success:
                    st.success("Replacement evidence uploaded and re-evaluated by AI! Complaint is now Under Review.")
                    st.rerun()
                else:
                    st.error("Failed to update evidence record.")


def render_my_complaints():
    user = st.session_state["user"]
    complaints = get_customer_complaints(user["id"])

    st.markdown("<h1 class='page-title'>My complaints</h1><div class='page-sub'>Track the status of the issues you reported.</div>", unsafe_allow_html=True)

    if not complaints:
        st.info("You haven't raised any complaints.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Go to My Bookings", width="stretch"):
                navigate_to("my_bookings")
        with c2:
            if st.button("Report an issue in chat", type="primary", width="stretch"):
                navigate_to("chat_assistant")
        return

    for cmp in complaints:
        with st.container(border=True):
            c_info, c_status = st.columns([3, 1.4])
            with c_info:
                st.markdown(f"**{cmp['category']}** · {cmp['space_name']}")
                st.markdown(
                    f"<div class='room-meta'>Complaint <code>{cmp['complaint_reference']}</code> · Booking <code>{cmp['booking_reference']}</code> · Raised {cmp['created_at'][:10]}</div>",
                    unsafe_allow_html=True,
                )
            with c_status:
                st.markdown(get_status_badge_html(cmp["status"]), unsafe_allow_html=True)
                st.caption(STATUS_HELP.get(cmp["status"], ""))

            with st.expander("View details & evidence"):
                detail = get_complaint_details(cmp["id"])
                st.markdown(f"**What you reported:** {detail['description']}")
                st.markdown(f"**Outcome you asked for:** {detail['expected_resolution']}")

                evidence_list = detail.get("evidence_list", [])
                has_unrelated = False

                if evidence_list:
                    st.markdown("**Uploaded Evidence:**")
                    for ev in evidence_list:
                        c_img, c_desc = st.columns([1, 2])
                        with c_img:
                            path = BASE_DIR / ev["file_path"]
                            if path.exists():
                                st.image(str(path), caption=ev["original_filename"], width="stretch")
                        with c_desc:
                            st.markdown(f"**Validation Status:** {get_status_badge_html(ev['validation_status'])}", unsafe_allow_html=True)
                            parsed = ev.get("parsed_result") or {}
                            if ev.get("validation_status") == "UNRELATED":
                                has_unrelated = True
                                st.warning(
                                    f"⚠️ **Image Not Valid for this Issue**\n\n"
                                    f"{parsed.get('explanation', 'The photo does not show technical proof.')}\n\n"
                                    f"**Tip:** {parsed.get('recommendation_for_customer', 'Please upload a speed test screenshot or router photo.')}"
                                )
                            else:
                                if parsed.get("explanation"):
                                    st.caption(parsed.get("explanation"))

                # If status is AWAITING EVIDENCE or image is UNRELATED, offer Re-upload button
                if cmp["status"] == "AWAITING EVIDENCE" or has_unrelated:
                    st.markdown(
                        "<div style='margin-top:0.8rem; padding:0.8rem; background:#FEF3C7; border:1px solid #F59E0B; border-radius:6px; color:#92400E;'>"
                        "<strong>Action Requested:</strong> Our review team needs valid technical proof to resolve your dispute. "
                        "Please click below to upload a speed test screenshot or router photo.</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("📤 Re-upload / Submit Correct Evidence", key=f"btn_open_reup_{cmp['id']}", type="primary"):
                        reupload_evidence_dialog(cmp)

                decision = detail.get("admin_decision")
                if decision:
                    st.success(
                        f"**Decision:** {resolution_label(decision['final_resolution'])}"
                        + (f" · ₹{decision['final_amount']:,.0f}" if decision["final_amount"] else "")
                        + f"\n\n{decision['reason']}"
                    )
                else:
                    if cmp["status"] != "AWAITING EVIDENCE" and not has_unrelated:
                        st.info("No decision yet. We'll update this page as soon as the review is complete.")
