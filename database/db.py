"""
Database connection and query utilities for SQLite.
Ensures thread-safe access, foreign key enforcement, and dictionary-like row access.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "database" / "coworking.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))

# Ensure the database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    """Return the absolute path to the active SQLite database."""
    return DB_PATH


@contextmanager
def get_db_connection():
    """Context manager yielding a SQLite connection with foreign keys and Row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(schema_path: Path = None):
    """Initialize the database schema from schema.sql."""
    if schema_path is None:
        schema_path = BASE_DIR / "database" / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db_connection() as conn:
        conn.executescript(schema_sql)

    ensure_schema_upgrades()


def execute_query(sql: str, params: tuple = ()) -> int:
    """Execute an UPDATE, DELETE or PRAGMA statement and return rows affected."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount


def execute_insert(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT statement and return the inserted row ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.lastrowid


def fetch_one(sql: str, params: tuple = ()):
    """Execute a query and fetch a single row as a dict, or None."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a query and return all matching rows as a list of dicts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def ensure_schema_upgrades():
    """
    Apply small, safe upgrades to databases created by an older version of the app.
    Currently: adds AI_INVESTIGATIONS.suggested_refund_amount if it is missing.
    """
    with get_db_connection() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "AI_INVESTIGATIONS" not in tables:
            return
        cols = {r[1] for r in conn.execute("PRAGMA table_info(AI_INVESTIGATIONS)")}
        if "suggested_refund_amount" not in cols:
            conn.execute("ALTER TABLE AI_INVESTIGATIONS ADD COLUMN suggested_refund_amount REAL")
