"""
Unit tests for FAISS policy retrieval, AI dispute adjudication, and admin decision persistence.
"""

import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.policy_service import retrieve_relevant_policies, build_faiss_index
from services.investigation_service import generate_dispute_investigation
from pages.dispute_details import save_admin_decision
from database.seed_data import seed_database
from database.db import fetch_one, fetch_all
from models.schemas import ProposedResolution


@pytest.fixture(autouse=True)
def setup_faiss():
    build_faiss_index()


def test_faiss_policy_retrieval():
    """Ensure FAISS indexes policies and returns relevant passages."""
    results = retrieve_relevant_policies("projector broken av screen failure", top_k=2)
    assert len(results) > 0
    assert any("amenity_malfunction" in r["source"] for r in results)


def test_ai_investigation_projector_partial_refund():
    """Case A: Projector failure in Meeting Room A yields PARTIAL_REFUND."""
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-001'")
    inv = generate_dispute_investigation(cmp["id"])

    assert inv.proposed_resolution == ProposedResolution.PARTIAL_REFUND
    assert inv.suggested_refund_percentage == 50.0
    assert len(inv.verified_facts) > 0
    assert len(inv.customer_allegations) > 0
    assert len(inv.owner_allegations) > 0
    assert len(inv.unknown_information) > 0


def test_ai_investigation_lockout_full_refund():
    """Case B: Customer lockout due to host PIN code change yields FULL_REFUND."""
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-002'")
    inv = generate_dispute_investigation(cmp["id"])

    assert inv.proposed_resolution == ProposedResolution.FULL_REFUND
    assert inv.suggested_refund_percentage == 100.0


def test_ai_investigation_garbage_bin_manual_review():
    """Case C: Wi-Fi complaint with garbage bin image yields MANUAL_INVESTIGATION."""
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-003'")
    inv = generate_dispute_investigation(cmp["id"])

    assert inv.proposed_resolution == ProposedResolution.MANUAL_INVESTIGATION
    assert inv.requires_manual_review is True
    assert inv.recommendation_for_admin is not None
    assert "additional evidence" in inv.recommendation_for_admin.lower() or "manual investigation" in inv.recommendation_for_admin.lower()


def test_ai_investigation_wifi_desk_mismatch():
    """Test that a Wi-Fi complaint with an uploaded desk photo yields MANUAL_INVESTIGATION and clear admin recommendation."""
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-7881'")
    if not cmp:
        # If DB was freshly initialized, query CMP-2026-003
        cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-003'")

    inv = generate_dispute_investigation(cmp["id"])
    assert inv.proposed_resolution == ProposedResolution.MANUAL_INVESTIGATION
    assert inv.requires_manual_review is True
    assert inv.suggested_refund_amount == 0.0
    assert any("mismatch" in issue.lower() or "unrelated" in issue.lower() for issue in inv.identified_issues)
    assert inv.recommendation_for_admin is not None



def test_ai_investigation_damage_dispute_manual_review():
    """Case D: Property damage dispute with conflicting accounts yields MANUAL_INVESTIGATION."""
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-004'")
    inv = generate_dispute_investigation(cmp["id"])

    assert inv.proposed_resolution == ProposedResolution.MANUAL_INVESTIGATION
    assert inv.requires_manual_review is True


def test_admin_decision_saving():
    """Ensure administrator decision is stored and updates complaint status in SQLite."""
    admin = fetch_one("SELECT id FROM USERS WHERE role = 'ADMIN'")
    cmp = fetch_one("SELECT id FROM COMPLAINTS WHERE complaint_reference = 'CMP-2026-001'")

    success = save_admin_decision(
        complaint_id=cmp["id"],
        admin_id=admin["id"],
        proposed_res="PARTIAL_REFUND",
        action="Approve AI Recommendation",
        final_res="PARTIAL_REFUND",
        reason="Host delayed maintenance response. Customer entitled to 50% refund under Amenity Malfunction Policy.",
        final_amount=750.0,
    )
    assert success is True

    # Check updated complaint status
    updated_cmp = fetch_one("SELECT status FROM COMPLAINTS WHERE id = ?", (cmp["id"],))
    assert updated_cmp["status"] == "RESOLVED"

    # Check decision record
    dec = fetch_one("SELECT * FROM ADMIN_DECISIONS WHERE complaint_id = ?", (cmp["id"],))
    assert dec is not None
    assert dec["action"] == "Approve AI Recommendation"
    assert dec["final_amount"] == 750.0

    # Check audit log
    audit = fetch_one("SELECT * FROM AUDIT_LOGS WHERE entity_id = ? ORDER BY id DESC LIMIT 1", (cmp["id"],))
    assert audit is not None
    assert "Approve AI Recommendation" in audit["action"]
