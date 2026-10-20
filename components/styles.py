"""
CSS Styling and UI helper classes for Streamlit.
Provides clean white background, dark blue headings, blue buttons,
rounded cards, and clear status badges.
"""

import streamlit as st


def apply_custom_styles():
    """Inject modern and accessible custom CSS styles into the Streamlit app."""
    custom_css = """
    <style>
    /* Google Fonts import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1E293B;
    }

    /* Background and container overrides */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        color: #1E3A8A !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* Buttons: primary = filled blue, secondary = outlined */
    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.1rem !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: 1px solid #2563EB !important;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25) !important;
    }
    .stButton > button[kind="secondary"], .stFormSubmitButton > button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #1E3A8A !important;
        border: 1px solid #CBD5E1 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #2563EB !important;
        color: #2563EB !important;
    }

    /* Top bar */
    .brand { font-size: 1.25rem; font-weight: 800; color: #1E3A8A; line-height: 1.1; }
    .brand span { color: #2563EB; }
    .brand-sub { font-size: 0.82rem; color: #64748B; }
    .nav-rule { margin: 0.6rem 0 1.4rem 0; border: none; border-top: 1px solid #E2E8F0; }

    /* Page headings */
    .page-title { margin: 0 0 0.2rem 0; font-size: 1.8rem; }
    .page-sub { color: #64748B; margin-bottom: 1.2rem; }

    /* Keep photos a sensible size */
    [data-testid="stImage"] img { max-height: 190px; object-fit: cover; border-radius: 8px; }

    /* Room cards */
    .room-price { font-size: 1.45rem; font-weight: 800; color: #1E3A8A; }
    .room-price small { font-size: 0.8rem; font-weight: 500; color: #64748B; }
    .room-meta { color: #64748B; font-size: 0.88rem; margin: 0.1rem 0 0.4rem 0; }
    .chip { display: inline-block; background: #F1F5F9; color: #334155; border-radius: 999px;
            padding: 0.15rem 0.6rem; font-size: 0.76rem; margin: 0 0.25rem 0.25rem 0; }
    .chip-best { background: #DCFCE7; color: #166534; font-weight: 700; }

    /* Booking summary box inside dialogs */
    .summary-box { background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px; padding: 0.9rem 1rem; margin: 0.6rem 0; }
    .summary-row { display: flex; justify-content: space-between; color: #1E40AF; padding: 0.12rem 0; }
    .summary-total { border-top: 1px dashed #93C5FD; margin-top: 0.4rem; padding-top: 0.5rem; font-weight: 800; font-size: 1.1rem; color: #1E3A8A; }

    /* Auth screen */
    .auth-hero { text-align: center; padding: 1.2rem 0 0.6rem 0; }
    .auth-hero h1 { font-size: 2.1rem; margin-bottom: 0.2rem; }
    .auth-hero p { color: #64748B; }

    /* Rounded UI Cards */
    .ui-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.25rem;
    }

    /* KPI metric cards */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    }
    .kpi-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin: 0.2rem 0;
    }
    .kpi-label {
        font-size: 0.88rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.3rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 600;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .badge-confirmed, .badge-resolved {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #BBF7D0;
    }
    .badge-submitted {
        background-color: #DBEAFE;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }
    .badge-under-review {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .badge-awaiting-evidence {
        background-color: #FFEDD5;
        color: #9A3412;
        border: 1px solid #FED7AA;
    }
    .badge-manual-investigation {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }
    .badge-closed {
        background-color: #F1F5F9;
        color: #475569;
        border: 1px solid #E2E8F0;
    }

    /* Demo badge */
    .demo-pill {
        display: inline-block;
        background-color: #F3E8FF;
        color: #6B21A8;
        border: 1px solid #E9D5FF;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Warning box for image mismatch */
    .mismatch-alert {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        color: #991B1B;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    /* Success box */
    .success-alert {
        background-color: #F0FDF4;
        border-left: 5px solid #22C55E;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        color: #166534;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    /* Space Card */
    .space-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def get_status_badge_html(status: str) -> str:
    """Return an HTML snippet for a styled status badge."""
    clean_status = (status or "").upper().strip()
    css_class = "badge-submitted"

    if clean_status in ("CONFIRMED", "RESOLVED"):
        css_class = "badge-confirmed"
    elif clean_status == "SUBMITTED":
        css_class = "badge-submitted"
    elif clean_status == "UNDER REVIEW":
        css_class = "badge-under-review"
    elif clean_status == "AWAITING EVIDENCE":
        css_class = "badge-awaiting-evidence"
    elif clean_status in ("MANUAL INVESTIGATION", "REJECTED"):
        css_class = "badge-manual-investigation"
    elif clean_status in ("CLOSED", "CANCELLED"):
        css_class = "badge-closed"

    return f'<span class="badge {css_class}">{clean_status}</span>'
