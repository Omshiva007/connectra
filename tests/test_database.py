"""
Tests for connectra_core.database (cross-platform paths, CRUD operations).
"""
import sqlite3
from pathlib import Path

import pytest


def test_data_dir_created(isolated_data_dir):
    """ensure_runtime() must create the data directory when it doesn't exist."""
    from connectra_core.database import ensure_runtime, DATA_DIR
    ensure_runtime()
    assert DATA_DIR.exists()


def test_database_file_is_inside_data_dir(isolated_data_dir):
    """The database file must live inside DATA_DIR, not a hardcoded path."""
    from connectra_core.database import DB_NAME, DATA_DIR
    assert str(DATA_DIR) in str(DB_NAME)


def test_database_creation(isolated_data_dir):
    """get_connection() must return a working SQLite connection."""
    from connectra_core.database import get_connection
    conn = get_connection()
    assert conn is not None
    conn.close()


def test_tables_created(isolated_data_dir):
    """All expected tables must be created on first connection."""
    from connectra_core.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "clients" in tables
    assert "contacts" in tables
    assert "email_logs" in tables


def test_insert_and_query_contact(isolated_data_dir):
    """Contacts can be inserted and retrieved correctly."""
    from connectra_core.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO contacts (email, domain) VALUES (?, ?)",
        ("alice@example.com", "example.com"),
    )
    conn.commit()

    cursor.execute("SELECT email FROM contacts WHERE email=?", ("alice@example.com",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "alice@example.com"


def test_no_hardcoded_windows_path(isolated_data_dir):
    """The database module must not contain a hardcoded C:/Connectra path."""
    import inspect
    import connectra_core.database as db_module
    source = inspect.getsource(db_module)
    assert "C:/Connectra" not in source
    assert "C:\\Connectra" not in source
