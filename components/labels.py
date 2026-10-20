"""Shared display helpers (labels and amount formatting) used by customer and admin pages."""

import re
from typing import Optional

RESOLUTION_LABELS = {
    "FULL_REFUND": "Full refund",
    "PARTIAL_REFUND": "Partial refund",
    "NO_REFUND": "No refund",
    "MANUAL_INVESTIGATION": "Manual review",
}


def resolution_label(value: Optional[str]) -> str:
    if not value:
        return "Pending"
    return RESOLUTION_LABELS.get(value, value.replace("_", " ").title())


def recommended_amount(proposed: Optional[str], booking_amount: float, stored: Optional[float], explanation: str = "") -> Optional[float]:
    """
    Refund amount behind an AI recommendation.
    Uses the stored amount when available; otherwise derives it only where the
    policy leaves no room for interpretation (full / no refund) or from the
    amount quoted in the AI explanation. Never invents a percentage.
    """
    if proposed == "FULL_REFUND":
        return float(booking_amount or 0)
    if proposed == "NO_REFUND":
        return 0.0
    if proposed == "PARTIAL_REFUND":
        if stored:
            return float(stored)
        match = re.search(r"₹\s?([\d,]+(?:\.\d+)?)", explanation or "")
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def money(value: Optional[float]) -> str:
    return "—" if value is None else f"₹{value:,.0f}"
