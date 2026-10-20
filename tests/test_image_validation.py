"""
Unit tests for Pillow image validation, size checks, and AI relevance classification.
"""

import sys
from pathlib import Path
import pytest
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.image_validation_service import validate_complaint_evidence
from services.gemini_service import get_demo_image_analysis
from models.schemas import ValidationStatus


def test_unrelated_image_mismatch_detection():
    """
    Test that uploading an unrelated image (garbage bin) for a Wi-Fi complaint
    triggers UNRELATED status and an Image Mismatch explanation.
    """
    res = get_demo_image_analysis(
        complaint_category="Wi-Fi Problem",
        complaint_description="The Wi-Fi was down all afternoon.",
        image_filename="garbage_bin.png",
    )
    assert res.validation_status == ValidationStatus.UNRELATED
    assert "image mismatch detected" in res.explanation.lower()
    assert "garbage bin" in res.explanation.lower()
    assert res.is_demo is True


def test_relevant_projector_image_validation():
    """
    Test that uploading a projector photograph for a Broken Equipment complaint
    is categorized as RELEVANT with caveats about static photography.
    """
    res = get_demo_image_analysis(
        complaint_category="Broken Equipment",
        complaint_description="Projector will not display video.",
        image_filename="projector_broken.png",
    )
    assert res.validation_status == ValidationStatus.RELEVANT
    assert "projector" in res.image_description.lower()
    assert len(res.limitations) > 0


def test_router_partially_relevant_validation():
    """
    Test that a router photograph for Wi-Fi problem is marked PARTIALLY_RELEVANT
    and explains that a photo cannot prove bandwidth failure.
    """
    res = get_demo_image_analysis(
        complaint_category="Wi-Fi Problem",
        complaint_description="Internet outage.",
        image_filename="router_wifi.png",
    )
    assert res.validation_status == ValidationStatus.PARTIALLY_RELEVANT
    assert "router" in res.image_description.lower()
    assert "cannot prove" in res.explanation.lower() or "cannot verify" in res.explanation.lower()


def test_unreadable_image_handling():
    """Test that a non-existent file returns IMAGE_UNREADABLE without raising an uncaught exception."""
    res = validate_complaint_evidence(
        image_path="non_existent_file_path_123.jpg",
        complaint_category="Broken Equipment",
        complaint_description="Broken chair",
    )
    assert res.validation_status == ValidationStatus.IMAGE_UNREADABLE


def test_wifi_complaint_with_desk_or_food_tray_is_unrelated():
    """
    Test that uploading a desk/food tray photo for a Wi-Fi complaint
    correctly classifies as UNRELATED and provides recommendations for customer and admin.
    """
    res = get_demo_image_analysis(
        complaint_category="Wi-Fi Problem",
        complaint_description="unable to connect the wifi",
        image_filename="images.jpeg",
    )
    assert res.validation_status == ValidationStatus.UNRELATED
    assert "mismatch" in res.explanation.lower()
    assert "desk" in res.image_description.lower() or "tray" in res.image_description.lower()
    assert res.recommendation_for_customer is not None
    assert "re-upload" in res.recommendation_for_customer.lower() or "speed test" in res.recommendation_for_customer.lower()
    assert res.recommendation_for_admin is not None
    assert "request additional evidence" in res.recommendation_for_admin.lower() or "manual investigation" in res.recommendation_for_admin.lower()


def test_cleanliness_complaint_with_desk_or_food_tray_is_relevant():
    """
    Test that the same desk/tray photo uploaded for a Cleanliness complaint
    is correctly classified as RELEVANT.
    """
    res = get_demo_image_analysis(
        complaint_category="Cleanliness Problem",
        complaint_description="table is not clean",
        image_filename="images.jpeg",
    )
    assert res.validation_status == ValidationStatus.RELEVANT
    assert "desk" in res.image_description.lower() or "table" in res.image_description.lower()


def test_wifi_speedtest_screenshot_is_relevant():
    """
    Test that a network diagnostic speed test screenshot is classified as RELEVANT for Wi-Fi.
    """
    res = get_demo_image_analysis(
        complaint_category="Wi-Fi Problem",
        complaint_description="0 Mbps internet outage",
        image_filename="speedtest_error_0mbps.png",
    )
    assert res.validation_status == ValidationStatus.RELEVANT
    assert "speed test" in res.image_description.lower() or "diagnostic" in res.image_description.lower()

