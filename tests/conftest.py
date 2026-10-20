"""
Pytest configuration and shared fixtures.
Ensures test database is cleanly seeded and test records are pruned between runs.
"""

import sys
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.seed_data import seed_database
from database.db import execute_query


@pytest.fixture(autouse=True)
def clean_and_seed_database():
    """Reset database to initial pristine demonstration state before each test."""
    seed_database()

    # Clean any dynamic records generated during tests so tests remain idempotent
    execute_query(
        "DELETE FROM BOOKINGS WHERE booking_reference NOT IN ('BK-2026-1001', 'BK-2026-1002', 'BK-2026-1003', 'BK-2026-1004')"
    )
    execute_query(
        "DELETE FROM USERS WHERE email NOT IN ('admin@coworking.com', 'alice@example.com', 'bob@example.com', 'charlie@example.com')"
    )
    execute_query(
        "DELETE FROM COMPLAINTS WHERE complaint_reference NOT IN ('CMP-2026-001', 'CMP-2026-002', 'CMP-2026-003', 'CMP-2026-004')"
    )
    execute_query(
        "DELETE FROM ADMIN_DECISIONS WHERE complaint_id NOT IN (SELECT id FROM COMPLAINTS WHERE complaint_reference IN ('CMP-2026-001', 'CMP-2026-002', 'CMP-2026-003', 'CMP-2026-004'))"
    )

    yield
