"""
Pydantic models for request validation, structured AI outputs, and domain types.
"""

from datetime import date, time, datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class SpaceCategory(str, Enum):
    MEETING_ROOM = "Meeting Room"
    PRIVATE_CABIN = "Private Cabin"
    DEDICATED_DESK = "Dedicated Desk"
    STUDIO = "Studio"
    DAY_PASS = "Day Pass"


class ComplaintCategory(str, Enum):
    WIFI = "Wi-Fi Problem"
    BROKEN_EQUIPMENT = "Broken Equipment"
    MISSING_AMENITY = "Missing Amenity"
    ACCESS_DENIED = "Access Denied"
    CLEANLINESS = "Cleanliness Problem"
    NOISE = "Noise Problem"
    MISLEADING_LISTING = "Misleading Listing"
    CANCELLATION = "Cancellation Dispute"
    PROPERTY_DAMAGE = "Property Damage"
    OTHER = "Other"


class ExpectedResolution(str, Enum):
    FULL_REFUND = "Full Refund"
    PARTIAL_REFUND = "Partial Refund"
    FIX_PROBLEM = "Fix the Problem"
    OTHER = "Other"


class ValidationStatus(str, Enum):
    RELEVANT = "RELEVANT"
    PARTIALLY_RELEVANT = "PARTIALLY_RELEVANT"
    UNRELATED = "UNRELATED"
    UNCERTAIN = "UNCERTAIN"
    IMAGE_UNREADABLE = "IMAGE_UNREADABLE"


class ComplaintStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER REVIEW"
    AWAITING_EVIDENCE = "AWAITING EVIDENCE"
    MANUAL_INVESTIGATION = "MANUAL INVESTIGATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ProposedResolution(str, Enum):
    FULL_REFUND = "FULL_REFUND"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    NO_REFUND = "NO_REFUND"
    MANUAL_INVESTIGATION = "MANUAL_INVESTIGATION"


# --- User Schemas ---
class CustomerRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


# --- Booking Schemas ---
class BookingCreateRequest(BaseModel):
    space_id: int
    booking_date: str  # YYYY-MM-DD
    start_time: str    # HH:MM
    end_time: str      # HH:MM
    number_of_people: int = Field(..., ge=1)


# --- AI Image Validation Schema ---
class ImageValidationOutput(BaseModel):
    image_description: str = Field(
        ..., description="Objective description of what is visibly depicted in the image."
    )
    complaint_category: str = Field(
        ..., description="The category of complaint reported by the customer."
    )
    validation_status: ValidationStatus = Field(
        ..., description="Assessment of whether the image provides relevant evidence for the complaint."
    )
    explanation: str = Field(
        ..., description="Clear explanation in plain language explaining the relevance determination."
    )
    visible_evidence: List[str] = Field(
        default_factory=list, description="Specific elements visible in the image that support or contradict the claim."
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Critical evidence that this photograph alone cannot prove or verify."
    )
    limitations: List[str] = Field(
        default_factory=list, description="Inherent limitations of photographic evidence for this specific dispute."
    )
    recommendation_for_customer: Optional[str] = Field(
        default=None, description="Clear guidance to customer on whether to re-upload or provide alternative proof."
    )
    recommendation_for_admin: Optional[str] = Field(
        default=None, description="Actionable guidance to admin regarding evidence validity and next investigative steps."
    )
    confidence_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Heuristic confidence rating (not a calibrated probability)."
    )
    is_demo: bool = Field(
        default=False, description="True if generated via simulated/demo logic instead of live Gemini API."
    )


# --- AI Dispute Investigation Schema ---
class DisputeInvestigationOutput(BaseModel):
    summary: str = Field(..., description="Concise summary of the dispute.")
    identified_issues: List[str] = Field(
        default_factory=list, description="Key issues raised in this dispute."
    )
    verified_facts: List[str] = Field(
        default_factory=list, description="Facts verified through database records, timestamps, or system logs."
    )
    customer_allegations: List[str] = Field(
        default_factory=list, description="Unverified claims made by the customer."
    )
    owner_allegations: List[str] = Field(
        default_factory=list, description="Unverified claims made by the space owner or management."
    )
    unknown_information: List[str] = Field(
        default_factory=list, description="Crucial facts that cannot be determined from available data."
    )
    supporting_evidence: List[str] = Field(
        default_factory=list, description="Evidence supporting the customer's or owner's position."
    )
    contradicting_evidence: List[str] = Field(
        default_factory=list, description="Evidence contradicting either party's statements."
    )
    missing_evidence: List[str] = Field(
        default_factory=list, description="Evidence still required to conclusively resolve the dispute."
    )
    policy_references: List[str] = Field(
        default_factory=list, description="Specific relevant policy clauses retrieved from knowledge base."
    )
    recommendation_for_admin: Optional[str] = Field(
        default=None, description="Clear, actionable recommendation for the administrator reviewing this case."
    )
    ai_explanation: str = Field(
        ..., description="Step-by-step reasoning tying verified facts and policy to the proposed resolution."
    )
    proposed_resolution: ProposedResolution = Field(
        ..., description="Recommended resolution based on facts and policy."
    )
    suggested_refund_percentage: Optional[float] = Field(
        default=0.0, description="Refund percentage explicitly justified by policy, if applicable."
    )
    suggested_refund_amount: Optional[float] = Field(
        default=0.0, description="Calculated refund amount in currency, if applicable."
    )
    requires_manual_review: bool = Field(
        default=False, description="Whether human administrator review and manual investigation are required."
    )
    uncertainty_level: str = Field(
        default="LOW", description="LOW, MEDIUM, or HIGH depending on evidence sufficiency."
    )
    is_demo: bool = Field(
        default=False, description="True if generated via simulated/demo logic."
    )


# --- Admin Decision Schema ---
class AdminDecisionCreate(BaseModel):
    complaint_id: int
    admin_id: int
    proposed_resolution: str
    final_resolution: str
    action: str  # Approve, Reject, Modify, Request Evidence, Manual Investigation
    reason: str = Field(..., min_length=5)
    final_amount: float = Field(default=0.0, ge=0.0)
