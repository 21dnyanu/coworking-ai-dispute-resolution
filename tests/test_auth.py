"""
Unit tests for authentication and role authorization.
"""

import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.auth_service import register_customer, authenticate_user, verify_user_role
from database.seed_data import seed_database
from database.db import fetch_one


def test_customer_registration_success():
    """Test creating a new customer account."""
    unique_email = "new_test_customer@example.com"
    # Ensure not present
    existing = fetch_one("SELECT id FROM USERS WHERE email = ?", (unique_email,))
    if existing:
        from database.db import execute_query
        execute_query("DELETE FROM USERS WHERE email = ?", (unique_email,))

    success, msg, user = register_customer("Test User", unique_email, "TestPass@123", "TestPass@123")
    assert success is True
    assert user is not None
    assert user["email"] == unique_email
    assert user["role"] == "CUSTOMER"


def test_customer_registration_duplicate_fails():
    """Test that duplicate registration with same email is rejected."""
    success, msg, user = register_customer("Alice Dupe", "alice@example.com", "Secret@123", "Secret@123")
    assert success is False
    assert "already registered" in msg.lower()
    assert user is None


def test_customer_registration_password_mismatch():
    """Test password confirmation mismatch."""
    success, msg, user = register_customer("Mismatched", "mismatch@example.com", "Secret123", "Secret456")
    assert success is False
    assert "passwords do not match" in msg.lower()


def test_customer_registration_short_password():
    """Test password length validation."""
    success, msg, user = register_customer("Short Pass", "short@example.com", "123", "123")
    assert success is False
    assert "at least 6 characters" in msg.lower()


def test_customer_login_success():
    """Test valid customer credentials."""
    success, msg, user = authenticate_user("alice@example.com", "Password@123", required_role="CUSTOMER")
    assert success is True
    assert user["email"] == "alice@example.com"
    assert user["role"] == "CUSTOMER"


def test_customer_login_invalid_password():
    """Test invalid password rejects login."""
    success, msg, user = authenticate_user("alice@example.com", "WrongPassword", required_role="CUSTOMER")
    assert success is False
    assert "invalid email or password" in msg.lower()
    assert user is None


def test_admin_login_success():
    """Test valid admin credentials."""
    success, msg, user = authenticate_user("admin@coworking.com", "Admin@123", required_role="ADMIN")
    assert success is True
    assert user["email"] == "admin@coworking.com"
    assert user["role"] == "ADMIN"


def test_role_enforcement_cross_access():
    """Ensure customer cannot log in via admin portal and vice versa."""
    # Customer trying to log in via Admin portal
    success, msg, user = authenticate_user("alice@example.com", "Password@123", required_role="ADMIN")
    assert success is False
    assert "strictly reserved for administrators" in msg.lower()

    # Admin trying to log in via Customer portal
    success, msg, user = authenticate_user("admin@coworking.com", "Admin@123", required_role="CUSTOMER")
    assert success is False
    assert "administrative accounts cannot log in via the customer portal" in msg.lower()
