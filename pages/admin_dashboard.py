"""
Admin dashboard: four KPIs and one complaints table
(complaint, booking, customer, space, category, amount, status, AI recommendation, admin decision).
Select a row to read the AI's proposed solution and open the full review.
"""

import pandas as pd
import streamlit as st
from database.db import fetch_one, fetch_all
from components.navigation import navigate_to
from components.labels import resolution_label, recommended_amount, money

STATUSES = ["All", "SUBMITTED", "UNDER REVIEW", "AWAITING EVIDENCE", "MANUAL INVESTIGATION", "RESOLVED", "CLOSED"]


def get_admin_metrics() -> dict:
    """Compute live admin KPI metrics from SQLite."""
    total_bk = fetch_one("SELECT COUNT(*) as cnt FROM BOOKINGS")["cnt"]
    total_cmp = fetch_one("SELECT COUNT(*) as cnt FROM COMPLAINTS")["cnt"]
    under_inv = fetch_one(
        "SELECT COUNT(*) as cnt FROM COMPLAINTS WHERE status IN ('SUBMITTED', 'UNDER REVIEW', 'AWAITING EVIDENCE')"
    )["cnt"]
    manual_req = fetch_one(
        """SELECT COUNT(DISTINCT c.id) as cnt
        FROM COMPLAINTS c
        LEFT JOIN AI_INVESTIGATIONS ai ON c.id = ai.complaint_id
        WHERE c.status = 'MANUAL INVESTIGATION' OR ai.requires_manual_review = 1"""
    )["cnt"]
    return {
        "total_bookings": total_bk,
        "total_complaints": total_cmp,
        "under_investigation": under_inv,
        "manual_review_required": manual_req,
    }


def load_case_rows(status: str = "All", search: str = "") -> list:
    """Complaints joined with booking, customer, space, AI recommendation and admin decision."""
    sql = """
        SELECT c.id, c.complaint_reference, c.category, c.status, c.customer_id,
               b.booking_reference, b.booking_amount,
               u.full_name AS customer_name,
               s.name AS space_name,
               ai.proposed_resolution AS ai_resolution, ai.explanation AS ai_explanation,
               ai.suggested_refund_amount AS ai_amount, ai.requires_manual_review,
               ad.final_resolution, ad.final_amount
        FROM COMPLAINTS c
        JOIN BOOKINGS b ON c.booking_id = b.id
        JOIN USERS u ON c.customer_id = u.id
        JOIN SPACES s ON b.space_id = s.id
        LEFT JOIN AI_INVESTIGATIONS ai ON c.id = ai.complaint_id
        LEFT JOIN ADMIN_DECISIONS ad ON c.id = ad.complaint_id
        WHERE 1=1
    """
    params = []
    if status != "All":
        sql += " AND c.status = ?"
        params.append(status)
    if search.strip():
        like = f"%{search.strip()}%"
        sql += " AND (c.complaint_reference LIKE ? OR b.booking_reference LIKE ? OR u.full_name LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY c.created_at DESC, c.id DESC"
    return fetch_all(sql, tuple(params))


def ai_recommendation_text(row: dict) -> str:
    if not row.get("ai_resolution"):
        return "Pending"
    label = resolution_label(row["ai_resolution"])
    amount = recommended_amount(row["ai_resolution"], row["booking_amount"], row.get("ai_amount"), row.get("ai_explanation", ""))
    if row["ai_resolution"] in ("FULL_REFUND", "PARTIAL_REFUND") and amount is not None:
        return f"{label} · {money(amount)}"
    return label


def admin_decision_text(row: dict) -> str:
    if not row.get("final_resolution"):
        return "Awaiting decision"
    label = resolution_label(row["final_resolution"])
    if row["final_resolution"] in ("FULL_REFUND", "PARTIAL_REFUND") and row.get("final_amount"):
        return f"{label} · {money(row['final_amount'])}"
    return label


def _kpi(col, label: str, value, color: str = "#1E3A8A"):
    col.markdown(
        f"<div class='kpi-card'><div class='kpi-label'>{label}</div><div class='kpi-number' style='color:{color}'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def render_admin_dashboard():
    metrics = get_admin_metrics()

    st.markdown("<h1 class='page-title'>Dashboard</h1><div class='page-sub'>Complaints, AI recommendations and your decisions in one place.</div>", unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, "Total bookings", metrics["total_bookings"])
    _kpi(k2, "Total complaints", metrics["total_complaints"])
    _kpi(k3, "Under investigation", metrics["under_investigation"], "#D97706")
    _kpi(k4, "Manual review", metrics["manual_review_required"], "#DC2626")

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    f1, f2, _ = st.columns([2, 1.5, 2])
    with f1:
        search = st.text_input("Search", placeholder="Complaint ID, booking ID or customer name", label_visibility="collapsed")
    with f2:
        status = st.selectbox("Status", STATUSES, label_visibility="collapsed", format_func=lambda s: "All statuses" if s == "All" else s.title())

    rows = load_case_rows(status, search)
    if not rows:
        st.info("No complaints match your filters.")
        return

    df = pd.DataFrame(
        {
            "Complaint ID": [r["complaint_reference"] for r in rows],
            "Booking ID": [r["booking_reference"] for r in rows],
            "Customer ID": [r["customer_id"] for r in rows],
            "Customer": [r["customer_name"] for r in rows],
            "Space": [r["space_name"] for r in rows],
            "Category": [r["category"] for r in rows],
            "Amount": [r["booking_amount"] for r in rows],
            "Status": [r["status"].title() for r in rows],
            "AI recommendation": [ai_recommendation_text(r) for r in rows],
            "Admin decision": [admin_decision_text(r) for r in rows],
        }
    )

    st.caption("Select a row to see the AI's proposed solution.")
    event = st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        key="admin_cases_table",
        column_config={"Amount": st.column_config.NumberColumn("Amount", format="₹%d"), "Customer ID": st.column_config.NumberColumn("Customer ID", format="%d")},
    )

    selected = event.selection.rows if event and event.selection else []
    if not selected:
        return

    row = rows[selected[0]]
    with st.container(border=True):
        st.markdown(f"#### {row['complaint_reference']} · {row['category']} · {row['customer_name']}")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**AI recommendation:** {ai_recommendation_text(row)}")
            if row.get("requires_manual_review"):
                st.warning("The AI flagged this case for manual review: evidence is missing or conflicting.")
            st.markdown(row.get("ai_explanation") or "The AI analysis is not available yet.")
            st.caption("The AI only proposes. Nothing is final until you approve, reject or modify it. No real refunds are processed.")
        with c2:
            if st.button("Review & decide", type="primary", width="stretch", key=f"review_{row['id']}"):
                navigate_to("admin_investigation", selected_complaint_id=row["id"])
