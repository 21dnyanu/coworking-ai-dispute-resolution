"""
Complaint form shown in a dialog from My Bookings.
Fields: issue category, details, optional photo (checked by Pillow + AI), expected resolution.
"""

import streamlit as st
from services.image_validation_service import validate_and_save_uploaded_image, validate_complaint_evidence
from services.complaint_service import create_complaint
from services.chat_service import COMPLAINT_CATEGORIES, EXPECTED_RESOLUTIONS
from components.navigation import navigate_to, set_flash


def check_photo(uploaded_file, category: str, description: str, cache_key: str):
    """Validate + AI-check a photo once per file. Returns (saved_path, validation_output, error)."""
    cache = st.session_state.setdefault("photo_cache", {})
    token = (uploaded_file.name, uploaded_file.size)
    cached = cache.get(cache_key)
    if cached and cached["token"] == token:
        return cached["path"], cached["result"], None

    with st.spinner("Checking your photo..."):
        ok, msg, dest = validate_and_save_uploaded_image(uploaded_file)
        if not ok:
            return None, None, msg
        result = validate_complaint_evidence(
            image_path=str(dest),
            complaint_category=category,
            complaint_description=description or category,
            original_filename=uploaded_file.name,
        )
    cache[cache_key] = {"token": token, "path": str(dest), "result": result}
    return str(dest), result, None


def render_photo_feedback(result):
    """Show the AI's relevance verdict for an uploaded photo. Returns True if it looks unrelated."""
    status = result.validation_status.value
    if status == "UNRELATED":
        st.error(
            f"⚠️ **Image Not Valid for this Issue**\n\n"
            f"{result.explanation}\n\n"
            f"💡 **Re-upload guidance:** {result.recommendation_for_customer or 'Please re-upload a photograph directly proving the issue (e.g. speed test screenshot or error screen), or submit without an image.'}"
        )
        return True
    if status in ("RELEVANT", "PARTIALLY_RELEVANT"):
        st.success("✅ Photo verified by AI and attached. It will be shared with the review team.")
        if status == "PARTIALLY_RELEVANT":
            st.caption(f"ℹ️ {result.explanation}")
    else:
        st.info(result.explanation)
    return False


def render_complaint_form(booking: dict, customer: dict):
    """The 4-field complaint form (call this inside a dialog)."""
    bid = booking["id"]
    st.markdown(
        f"**{booking['space_name']}** · {booking['booking_date']} · {booking['start_time']}–{booking['end_time']} · ₹{booking['booking_amount']:,.0f}"
    )

    category = st.selectbox("What was the issue?", COMPLAINT_CATEGORIES, key=f"cf_cat_{bid}")
    description = st.text_area(
        "Tell us what happened",
        placeholder="e.g. The projector didn't turn on and the front desk had no replacement.",
        height=110,
        key=f"cf_desc_{bid}",
    )
    photo = st.file_uploader("Add a photo (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"cf_photo_{bid}")

    ev_path = ev_result = None
    ev_name = photo.name if photo else None
    use_photo = True
    if photo is not None:
        ev_path, ev_result, err = check_photo(photo, category, description, f"form_{bid}")
        if err:
            st.error(err)
        elif ev_result is not None:
            unrelated = render_photo_feedback(ev_result)
            if unrelated:
                skip_unrelated = st.checkbox(
                    "Submit without this photo (Recommended)",
                    value=True,
                    key=f"cf_skip_{bid}",
                    help="Uncheck this if you still want to attach the photo despite the mismatch warning.",
                )
                use_photo = not skip_unrelated
                if not skip_unrelated:
                    st.caption("⚠️ If submitted with an unrelated image, the complaint will be flagged for evidence re-upload and manual review.")

    resolution = st.selectbox(
        "What outcome would you like?",
        EXPECTED_RESOLUTIONS,
        help="This is your request, not the final decision.",
        key=f"cf_res_{bid}",
    )

    if st.button("Submit complaint", type="primary", width="stretch", key=f"cf_submit_{bid}"):
        attach = bool(ev_path) and use_photo
        ok, msg, complaint = create_complaint(
            customer_id=customer["id"],
            booking_id=bid,
            category=category,
            description=description,
            expected_resolution=resolution,
            evidence_file_path=ev_path if attach else None,
            original_filename=ev_name if attach else None,
            validation_status=ev_result.validation_status.value if attach and ev_result else None,
            validation_result=ev_result.model_dump(mode="json") if attach and ev_result else None,
        )
        if ok:
            set_flash(f"Complaint {complaint['complaint_reference']} submitted. Track it in My Complaints.", "📨")
            navigate_to("my_complaints")
        else:
            st.error(msg)
