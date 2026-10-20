"""
Navigation and session routing controller.
Guarantees backend authorization checks and prevents privilege escalation.
"""

import streamlit as st

CUSTOMER_TABS = [
    ("home", "🏠 Home"),
    ("my_bookings", "📅 My Bookings"),
    ("my_complaints", "📋 My Complaints"),
    ("chat_assistant", "💬 Chat Help"),
]


def init_session_state():
    """Ensure baseline session variables exist."""
    defaults = {
        "current_page": "auth",
        "user": None,
        "selected_complaint_id": None,
        "flash": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def navigate_to(page_name: str, **kwargs):
    """Navigate to target page and optionally set parameters."""
    st.session_state["current_page"] = page_name
    for key, value in kwargs.items():
        st.session_state[key] = value
    st.rerun()


def set_flash(message: str, icon: str = "✅"):
    """Queue a confirmation banner that is shown at the top of the next page."""
    st.session_state["flash"] = (message, icon)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash[0], icon=flash[1])


def logout():
    """Clear the whole session and return to the login page."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["current_page"] = "auth"
    st.rerun()


def render_navbar():
    """Render the top navigation bar for the signed-in role."""
    user = st.session_state.get("user")
    if not user:
        return

    current = st.session_state.get("current_page")

    if user.get("role") == "CUSTOMER":
        cols = st.columns([2.6] + [1.3] * len(CUSTOMER_TABS) + [1])
        with cols[0]:
            st.markdown(
                f"<div class='brand'>🏢 CoWork<span>Hub</span></div>"
                f"<div class='brand-sub'>Hi, {user['full_name'].split()[0]}</div>",
                unsafe_allow_html=True,
            )
        for col, (page, label) in zip(cols[1:-1], CUSTOMER_TABS):
            with col:
                if st.button(label, key=f"nav_{page}", width="stretch", type="primary" if current == page else "secondary"):
                    navigate_to(page)
        with cols[-1]:
            if st.button("Logout", key="nav_logout", width="stretch", type="secondary"):
                logout()

    elif user.get("role") == "ADMIN":
        cols = st.columns([4, 1.4, 1])
        with cols[0]:
            st.markdown(
                f"<div class='brand'>🛡️ CoWork<span>Hub</span> Admin</div>"
                f"<div class='brand-sub'>{user['full_name']}</div>",
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button("📊 Dashboard", key="nav_admin_dash", width="stretch", type="primary" if current == "admin_dashboard" else "secondary"):
                navigate_to("admin_dashboard")
        with cols[2]:
            if st.button("Logout", key="nav_logout", width="stretch", type="secondary"):
                logout()

    st.markdown("<hr class='nav-rule'/>", unsafe_allow_html=True)

    # Render optional settings in sidebar
    with st.sidebar:
        st.markdown("### ⚙️ AI Engine Settings")
        api_key_val = st.text_input(
            "Gemini API Key (Optional)",
            value=st.session_state.get("sidebar_gemini_api_key", ""),
            type="password",
            help="Leave blank to use smart policy-grounded Demo Mode. Enter a Google Gemini API key to activate live multimodal Vision.",
            key="input_gemini_key",
        )
        if api_key_val != st.session_state.get("sidebar_gemini_api_key", ""):
            st.session_state["sidebar_gemini_api_key"] = api_key_val
            st.rerun()

        from services.gemini_service import is_live_api_configured
        if is_live_api_configured():
            st.success("🟢 Mode: Live Gemini AI Active")
        else:
            st.info("🟡 Mode: Policy Demo Mode Active (Offline Safe)")



def check_page_authorization(required_role: str) -> bool:
    """
    Enforce backend role authorization.
    Redirects unauthorized attempts back to the login screen.
    """
    user = st.session_state.get("user")
    if not user or user.get("role") != required_role:
        st.session_state["current_page"] = "auth"
        st.error(f"Unauthorized access. This view requires {required_role} credentials.")
        st.rerun()
        return False
    return True
