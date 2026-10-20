"""
Chat Help: a guided assistant that files a complaint through conversation.

Flow: issue -> booking -> category check -> photo -> desired outcome -> confirm -> submit.
It also answers "what's the status of my complaint?".
"""

import streamlit as st
from services.booking_service import get_customer_bookings
from services.complaint_service import get_customer_complaints, create_complaint
from services.chat_service import (
    COMPLAINT_CATEGORIES,
    EXPECTED_RESOLUTIONS,
    detect_category,
    is_status_question,
    is_greeting,
    format_status_reply,
)
from components.complaint_form import check_photo, render_photo_feedback
from components.navigation import navigate_to

GREETING = "Hi! 👋 I can help you report a problem with a booking. Just tell me what went wrong — for example *“the projector didn't work”*."


def _fresh_state() -> dict:
    return {
        "messages": [{"role": "assistant", "text": GREETING}],
        "step": "issue",  # issue -> booking -> category -> photo -> resolution -> confirm -> done
        "data": {},
    }


def _say(role: str, text: str):
    st.session_state["chat"]["messages"].append({"role": role, "text": text})


def _go(step: str):
    st.session_state["chat"]["step"] = step
    st.rerun()


def _eligible_bookings(user_id: int):
    return [b for b in get_customer_bookings(user_id) if not b.get("complaint_id") and b["status"] != "CANCELLED"]


def _ask_booking_or_stop(user_id: int):
    """After the issue is known, ask which booking it relates to."""
    bookings = _eligible_bookings(user_id)
    if not bookings:
        _say("assistant", "I couldn't find a booking without an existing complaint. Each booking can have one complaint — check **My Complaints** for its status.")
        st.session_state["chat"]["step"] = "done"
        return
    if len(bookings) == 1:
        b = bookings[0]
        st.session_state["chat"]["data"]["booking"] = b
        _say("assistant", f"Is this about **{b['space_name']}** on {b['booking_date']}? I'll use that booking.")
        _ask_category()
        return
    _say("assistant", "Which booking is this about?")
    st.session_state["chat"]["step"] = "booking"


def _ask_category():
    data = st.session_state["chat"]["data"]
    data["category"] = detect_category(data["description"])
    _say("assistant", f"This sounds like a **{data['category']}** issue. Is that right?")
    st.session_state["chat"]["step"] = "category"


def render_chat_assistant():
    user = st.session_state["user"]
    if "chat" not in st.session_state:
        st.session_state["chat"] = _fresh_state()
    chat = st.session_state["chat"]
    data = chat["data"]

    head, reset = st.columns([5, 1])
    with head:
        st.markdown("<h1 class='page-title'>Chat help</h1><div class='page-sub'>Describe the problem and I'll file the complaint for you.</div>", unsafe_allow_html=True)
    with reset:
        if st.button("New chat", width="stretch"):
            st.session_state["chat"] = _fresh_state()
            st.rerun()

    for m in chat["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])

    step = chat["step"]

    # ---- Interactive step widgets (rendered as the assistant's turn) ----
    if step == "booking":
        with st.chat_message("assistant"):
            bookings = _eligible_bookings(user["id"])
            labels = {f"{b['space_name']} · {b['booking_date']} · {b['booking_reference']}": b for b in bookings}
            choice = st.selectbox("Choose a booking", list(labels.keys()), key="chat_booking_pick", label_visibility="collapsed")
            if st.button("Use this booking", type="primary", key="chat_booking_go"):
                data["booking"] = labels[choice]
                _say("user", choice)
                _ask_category()
                st.rerun()

    elif step == "category":
        with st.chat_message("assistant"):
            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("Yes, that's right", type="primary", key="chat_cat_yes", width="stretch"):
                    _say("user", f"Yes — {data['category']}")
                    _say("assistant", "Got it. Do you have a photo of the problem? A photo helps, but it's optional.")
                    _go("photo")
            with c2:
                other = st.selectbox("Or pick another category", COMPLAINT_CATEGORIES, index=COMPLAINT_CATEGORIES.index(data["category"]), key="chat_cat_pick")
                if other != data["category"] and st.button("Use this category", key="chat_cat_change"):
                    data["category"] = other
                    _say("user", f"It's a {other} issue")
                    _say("assistant", "Thanks. Do you have a photo of the problem? A photo helps, but it's optional.")
                    _go("photo")

    elif step == "photo":
        with st.chat_message("assistant"):
            photo = st.file_uploader("Upload a photo", type=["png", "jpg", "jpeg", "webp"], key="chat_photo", label_visibility="collapsed")
            if photo is not None:
                path, result, err = check_photo(photo, data["category"], data["description"], "chat")
                if err:
                    st.error(err)
                elif result is not None:
                    unrelated = render_photo_feedback(result)
                    if unrelated:
                        st.info("Please choose a different photo above (such as a speed test screenshot or error screen), or click **Skip — no photo** below.")
                    elif st.button("Use this photo", type="primary", key="chat_photo_use"):
                        data.update(evidence_path=path, evidence_name=photo.name, evidence_result=result)
                        _say("user", f"📷 {photo.name}")
                        _say("assistant", "Photo saved. What outcome would you like?")
                        _go("resolution")
            if st.button("Skip — no photo", key="chat_photo_skip"):
                _say("user", "No photo")
                _say("assistant", "No problem. What outcome would you like?")
                _go("resolution")

    elif step == "resolution":
        with st.chat_message("assistant"):
            cols = st.columns(len(EXPECTED_RESOLUTIONS))
            for col, res in zip(cols, EXPECTED_RESOLUTIONS):
                with col:
                    if st.button(res, key=f"chat_res_{res}", width="stretch"):
                        data["resolution"] = res
                        _say("user", res)
                        b = data["booking"]
                        _say(
                            "assistant",
                            "Here's what I'll submit:\n\n"
                            f"- **Booking:** {b['space_name']} · {b['booking_date']} (₹{b['booking_amount']:,.0f})\n"
                            f"- **Issue:** {data['category']}\n"
                            f"- **Details:** {data['description']}\n"
                            f"- **Photo:** {'attached' if data.get('evidence_path') else 'none'}\n"
                            f"- **You'd like:** {res}\n\nShall I submit it?",
                        )
                        _go("confirm")

    elif step == "confirm":
        with st.chat_message("assistant"):
            c1, c2, _ = st.columns([1, 1, 2])
            with c1:
                if st.button("Submit complaint", type="primary", key="chat_submit", width="stretch"):
                    result = data.get("evidence_result")
                    ok, msg, complaint = create_complaint(
                        customer_id=user["id"],
                        booking_id=data["booking"]["id"],
                        category=data["category"],
                        description=data["description"],
                        expected_resolution=data["resolution"],
                        evidence_file_path=data.get("evidence_path"),
                        original_filename=data.get("evidence_name"),
                        validation_status=result.validation_status.value if result else None,
                        validation_result=result.model_dump(mode="json") if result else None,
                    )
                    _say("user", "Submit")
                    if ok:
                        _say("assistant", f"✅ Done! Your complaint **{complaint['complaint_reference']}** has been submitted. You can follow its status in **My Complaints**.")
                    else:
                        _say("assistant", f"Sorry, I couldn't submit that: {msg}")
                    _go("done")
            with c2:
                if st.button("Start over", key="chat_restart", width="stretch"):
                    st.session_state["chat"] = _fresh_state()
                    st.rerun()

    elif step == "done":
        c1, c2, _ = st.columns([1.2, 1, 2])
        with c1:
            if st.button("Open My Complaints", type="primary", key="chat_open_cmp", width="stretch"):
                navigate_to("my_complaints")
        with c2:
            if st.button("New chat", key="chat_new_done", width="stretch"):
                st.session_state["chat"] = _fresh_state()
                st.rerun()

    # ---- Free-text input ----
    placeholder = "Describe the problem..." if step in ("issue", "done") else "Ask about your complaint status..."
    text = st.chat_input(placeholder)
    if text:
        _say("user", text)
        if is_status_question(text):
            _say("assistant", format_status_reply(get_customer_complaints(user["id"])))
        elif step == "issue":
            if is_greeting(text):
                _say("assistant", "Hello! Tell me what went wrong with your booking and I'll take it from there.")
            else:
                data["description"] = text.strip()
                if len(data["description"]) < 10:
                    _say("assistant", "Could you add a bit more detail? A sentence or two is perfect.")
                else:
                    _ask_booking_or_stop(user["id"])
        elif step == "done":
            if is_greeting(text):
                _say("assistant", "Hi again! Use **New chat** to report another issue.")
            else:
                _say("assistant", "To report another issue, press **New chat**.")
        else:
            _say("assistant", "Please use the buttons above to continue, or press **New chat** to start over.")
        st.rerun()
