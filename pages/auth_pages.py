"""
Single sign-in screen: Login (customer or admin) and customer registration.
"""

import streamlit as st
from services.auth_service import register_customer, authenticate_user
from components.navigation import navigate_to


def _after_login(user: dict):
    st.session_state["user"] = user
    navigate_to("admin_dashboard" if user["role"] == "ADMIN" else "home")


def render_auth_page():
    """Render the login / register screen."""
    _, center, _ = st.columns([1, 1.6, 1])

    with center:
        st.markdown(
            """
            <div class="auth-hero">
                <div class="brand" style="font-size:1.6rem;">🏢 CoWork<span>Hub</span></div>
                <h1>Book a space. Get help fast.</h1>
                <p>Meeting rooms, cabins, desks and studios — and a quick way to report problems.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Login", "Create account"])

            with tab_login:
                role_label = st.radio("I am a", ["Customer", "Admin"], horizontal=True, key="login_role")
                with st.form("login_form"):
                    email = st.text_input("Email", placeholder="name@example.com")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Login", type="primary", width="stretch")

                if submit:
                    role = "ADMIN" if role_label == "Admin" else "CUSTOMER"
                    ok, msg, user = authenticate_user(email, password, required_role=role)
                    if ok:
                        _after_login(user)
                    else:
                        st.error(msg)

            with tab_register:
                with st.form("register_form"):
                    full_name = st.text_input("Full name", placeholder="Jane Doe")
                    email = st.text_input("Email", placeholder="jane@example.com", key="reg_email")
                    password = st.text_input("Password", type="password", placeholder="At least 6 characters", key="reg_pwd")
                    confirm = st.text_input("Confirm password", type="password")
                    submit = st.form_submit_button("Create account", type="primary", width="stretch")

                if submit:
                    ok, msg, user = register_customer(full_name, email, password, confirm)
                    if ok:
                        _after_login(user)
                    else:
                        st.error(msg)

        with st.expander("Demo accounts"):
            st.markdown(
                """
                - **Customer:** `alice@example.com` / `Password@123`
                - **Customer:** `bob@example.com` / `Password@123`
                - **Admin:** `admin@coworking.com` / `Admin@123`
                """
            )
