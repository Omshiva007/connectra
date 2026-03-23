"""Pytest configuration, fixtures and shared utilities for Connectra tests."""

import sqlite3
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Make sure the repo root is on sys.path so that `connectra_core` imports work
# without the package being installed.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_fernet():
    """Reset the cached Fernet instance between tests so key changes take effect."""
    from connectra_core.security import reset_fernet
    reset_fernet()
    yield
    reset_fernet()


# ---------------------------------------------------------------------------
# In-memory / temp-file databases
# ---------------------------------------------------------------------------

def _make_user_db(tmp_path) -> str:
    """Create and initialise a user SQLite database in *tmp_path*, return its path."""
    db_path = str(tmp_path / "connectra_user.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS contacts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            domain TEXT
        );
        CREATE TABLE IF NOT EXISTS email_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_email TEXT,
            client_domain TEXT,
            template_name TEXT,
            recipient_count INTEGER
        );
    """)
    conn.commit()
    conn.close()
    return db_path


def _make_admin_db(tmp_path) -> str:
    """Create and initialise an admin SQLite database in *tmp_path*, return its path."""
    db_path = str(tmp_path / "connectra_admin.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            app_password TEXT,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS settings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS holiday_calendar(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            holiday TEXT,
            date TEXT,
            template TEXT,
            reminder_days INTEGER,
            active INTEGER DEFAULT 1
        );
    """)
    conn.commit()
    conn.close()
    return db_path


def _open_wal(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection in WAL mode."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@pytest.fixture()
def user_db_conn(tmp_path):
    """Provide an isolated user database for a test.

    Patches :func:`connectra_core.database.get_connection` and
    :func:`connectra_core.email_sender.get_connection` to use a WAL-mode
    temp-file SQLite database so the code under test can open/close
    connections freely while data persists for the duration of the test.

    Yields an open connection for use in assertions.  Uses WAL journal mode
    so concurrent connections do not deadlock each other.
    """
    db_path = _make_user_db(tmp_path)

    def _factory():
        return _open_wal(db_path)

    with patch("connectra_core.database.get_connection", side_effect=_factory), \
         patch("connectra_core.email_sender.get_connection", side_effect=_factory):
        conn = _open_wal(db_path)
        yield conn
        conn.close()


@pytest.fixture()
def admin_db_conn(tmp_path):
    """Provide an isolated admin database for a test.

    Patches :func:`connectra_core.admin_database.get_connection` and
    :func:`connectra_core.holiday_checker.get_connection` to use a WAL-mode
    temp-file SQLite database.  Also patches the ``ADMIN_DB.exists()`` path
    guard in holiday_checker so it does not return early.

    Yields an open connection for use in assertions.
    """
    db_path = _make_admin_db(tmp_path)

    def _factory():
        return _open_wal(db_path)

    with patch("connectra_core.admin_database.get_connection", side_effect=_factory), \
         patch("connectra_core.holiday_checker.get_connection", side_effect=_factory), \
         patch("connectra_core.holiday_checker.ADMIN_DB") as mock_path:
        mock_path.exists.return_value = True
        conn = _open_wal(db_path)
        yield conn
        conn.close()


# ---------------------------------------------------------------------------
# Mock SMTP server
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_smtp():
    """Patch smtplib.SMTP so no real network connections are made."""
    mock_server = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_server) as mock_cls:
        yield mock_cls, mock_server


# ---------------------------------------------------------------------------
# Temporary template directory
# ---------------------------------------------------------------------------

@pytest.fixture()
def template_dir(tmp_path):
    """Create a temporary directory containing a sample JSON template."""
    t = tmp_path / "templates"
    t.mkdir()
    sample = {
        "name": "Happy New Year",
        "subject": "Happy New Year from Connectra",
        "body": "<p>Wishing you a wonderful year!</p>",
    }
    (t / "happy_new_year.json").write_text(json.dumps(sample), encoding="utf-8")
    return t


# ---------------------------------------------------------------------------
# Factory helpers (test data)
# ---------------------------------------------------------------------------

def make_user(email: str = "user@example.com", password: str = "app_pass_123") -> dict:
    """Return a minimal user dict."""
    return {"email": email, "app_password": password}


def make_holiday(
    holiday: str = "New Year",
    date: str = "2026-01-01",
    template: str = "Happy New Year",
    reminder_days: int = 7,
    active: int = 1,
) -> dict:
    return {
        "holiday": holiday,
        "date": date,
        "template": template,
        "reminder_days": reminder_days,
        "active": active,
    }


def make_contact(email: str = "client@acme.com", domain: str = "acme.com") -> dict:
    return {"email": email, "domain": domain}
