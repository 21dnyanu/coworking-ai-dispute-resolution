"""
Authentication and Authorization service.
Handles customer registration, credential verification via Werkzeug,
and role-based access control.
"""

import re
from typing import Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import fetch_one, execute_insert, execute_query


def validate_email_format(email: str) -> bool:
    """Basic regex check for email format."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


def register_customer(
    full_name: str, email: str, password: str, confirm_password: str
) -> Tuple[bool, str, Optional[dict]]:
    """
    Register a new customer account.
    Returns (success, message, user_dict).
    """
    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        return False, "Full Name is required.", None

    if len(full_name) < 2:
        return False, "Full Name must be at least 2 characters.", None

    if not email or not validate_email_format(email):
        return False, "Please enter a valid email address.", None

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    if password != confirm_password:
        return False, "Passwords do not match.", None

    # Check for existing email
    existing_user = fetch_one("SELECT id FROM USERS WHERE email = ?", (email,))
    if existing_user:
        return False, "This email is already registered. Please login instead.", None

    # Hash password safely
    pwd_hash = generate_password_hash(password)

    try:
        user_id = execute_insert(
            "INSERT INTO USERS (full_name, email, password_hash, role) VALUES (?, ?, ?, 'CUSTOMER')",
            (full_name, email, pwd_hash),
        )
        new_user = fetch_one("SELECT id, full_name, email, role, created_at FROM USERS WHERE id = ?", (user_id,))
        return True, "Registration successful!", new_user
    except Exception as e:
        return False, f"Registration failed due to a database error: {str(e)}", None


def authenticate_user(email: str, password: str, required_role: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
    """
    Authenticate user with email and password.
    Enforces optional role requirement (e.g. CUSTOMER vs ADMIN).
    Returns (success, message, user_dict).
    """
    email = email.strip().lower()
    if not email or not password:
        return False, "Please provide both email and password.", None

    user = fetch_one("SELECT id, full_name, email, password_hash, role, created_at FROM USERS WHERE email = ?", (email,))
    if not user:
        return False, "Invalid email or password. Please try again.", None

    if not check_password_hash(user["password_hash"], password):
        return False, "Invalid email or password. Please try again.", None

    if required_role and user["role"] != required_role:
        if required_role == "ADMIN":
            return False, "Access denied. This login portal is strictly reserved for administrators.", None
        elif required_role == "CUSTOMER":
            return False, "Administrative accounts cannot log in via the customer portal. Please use the Admin Login.", None

    # Exclude password_hash from returned user dictionary
    user_data = {
        "id": user["id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }
    return True, "Login successful!", user_data


def verify_user_role(user: Optional[dict], expected_role: str) -> bool:
    """Check if the provided user dict has the expected role."""
    if not user or not isinstance(user, dict):
        return False
    return user.get("role") == expected_role
