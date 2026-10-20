"""
Rule-based helpers for the customer chat assistant.

The chat collects exactly the same information as the complaint form
(booking, category, details, optional photo, expected resolution) and then
calls the normal `create_complaint` service, so the AI investigation and the
admin review work in the same way for both entry points.
"""

import re
from typing import List, Optional

COMPLAINT_CATEGORIES = [
    "Wi-Fi Problem",
    "Broken Equipment",
    "Missing Amenity",
    "Access Denied",
    "Cleanliness Problem",
    "Noise Problem",
    "Misleading Listing",
    "Cancellation Dispute",
    "Property Damage",
    "Other",
]

EXPECTED_RESOLUTIONS = ["Full Refund", "Partial Refund", "Fix the Problem", "Other"]

# Order matters: the first category with a matching keyword wins.
_CATEGORY_KEYWORDS = [
    ("Access Denied", ["locked out", "lock", "pin", "keycard", "key card", "denied", "could not enter", "couldn't enter", "can't enter", "cannot enter", "door"]),
    ("Wi-Fi Problem", ["wifi", "wi-fi", "internet", "network", "disconnect", "router", "slow connection"]),
    ("Broken Equipment", ["projector", "broken", "not working", "not turn on", "monitor", "screen", "ac ", "air condition", "equipment", "printer", "socket", "not functional"]),
    ("Missing Amenity", ["missing", "not provided", "no whiteboard", "no coffee", "advertised", "was not available", "wasn't available"]),
    ("Cleanliness Problem", ["dirty", "unclean", "clean", "garbage", "smell", "trash", "dust"]),
    ("Noise Problem", ["noise", "noisy", "loud", "music", "disturb"]),
    ("Property Damage", ["damage", "damaged", "scratch", "stain", "broke the", "spilled"]),
    ("Cancellation Dispute", ["cancel", "cancellation", "refund policy"]),
    ("Misleading Listing", ["misleading", "not as described", "different from", "photos do not match", "looks different"]),
]

_STATUS_WORDS = ["status", "track", "progress", "update on", "where is my complaint", "my complaints", "any update"]
_GREETING_WORDS = ["hi", "hello", "hey", "help", "start"]


def detect_category(text: str) -> str:
    """Guess the complaint category from free text. Falls back to 'Other'."""
    lowered = f" {text.lower()} "
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return category
    return "Other"


def is_status_question(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _STATUS_WORDS)


def is_greeting(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    return bool(words) and len(words) <= 3 and words[0] in _GREETING_WORDS


def format_status_reply(complaints: List[dict]) -> str:
    """Plain-language reply listing the customer's complaints and their statuses."""
    if not complaints:
        return "You haven't raised any complaints yet. Tell me what went wrong and I'll help you file one."

    lines = ["Here is where your complaints stand:"]
    for c in complaints[:5]:
        outcome = c.get("final_resolution")
        extra = f" — decision: **{outcome.replace('_', ' ').title()}**" if outcome else ""
        lines.append(f"- `{c['complaint_reference']}` · {c['category']} · **{c['status'].title()}**{extra}")
    return "\n".join(lines)
