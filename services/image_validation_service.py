"""
Image processing, validation, and file management service.
Uses Pillow for image verification and Gemini service for multimodal analysis.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from dotenv import load_dotenv
from models.schemas import ImageValidationOutput, ValidationStatus
from services.gemini_service import analyze_complaint_image_with_gemini

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIRECTORY", "uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5")) * 1024 * 1024  # 5MB in bytes


def validate_and_save_uploaded_image(
    uploaded_file,
) -> Tuple[bool, str, Optional[Path]]:
    """
    Validate uploaded image using Pillow and save to uploads/ directory.
    Returns (success, message, saved_path).
    """
    if uploaded_file is None:
        return False, "No file uploaded.", None

    # Check file size
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE // (1024 * 1024)
        return False, f"File size exceeds the {max_mb}MB limit. Please upload a smaller image.", None

    # Verify image integrity using Pillow
    try:
        image = Image.open(uploaded_file)
        image.verify()
        # Reset file pointer after verify
        uploaded_file.seek(0)
        # Re-open to read format
        img_reopened = Image.open(uploaded_file)
        ext = (img_reopened.format or "PNG").lower()
        if ext == "jpeg":
            ext = "jpg"
    except Exception as e:
        return False, f"Invalid or corrupted image file: {str(e)}", None

    # Generate safe unique filename
    safe_name = f"evidence_{uuid.uuid4().hex[:12]}.{ext}"
    dest_path = UPLOAD_DIR / safe_name

    try:
        uploaded_file.seek(0)
        with open(dest_path, "wb") as f:
            f.write(uploaded_file.read())
        return True, "Image uploaded and verified successfully.", dest_path
    except Exception as e:
        return False, f"Failed to save image to server: {str(e)}", None


def validate_complaint_evidence(
    image_path: str,
    complaint_category: str,
    complaint_description: str,
    original_filename: Optional[str] = None,
) -> ImageValidationOutput:
    """Run AI image validation on saved file and return Pydantic structured output."""
    return analyze_complaint_image_with_gemini(
        image_path=image_path,
        complaint_category=complaint_category,
        complaint_description=complaint_description,
        original_filename=original_filename,
    )
