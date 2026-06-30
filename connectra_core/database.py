"""User desktop database helpers for contacts, domains, and send logs."""

import sqlite3

from connectra_core.config import DATA_DIR

DB_NAME = DATA_DIR / "connectra_user.db"


def ensure_runtime():
    """Create the user data directory before opening SQLite files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Open the user SQLite database and ensure all user tables exist."""

    ensure_runtime()

    conn = sqlite3.connect(str(DB_NAME))

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        domain TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_email TEXT,
        client_domain TEXT,
        template_name TEXT,
        recipient_count INTEGER
    )
    """)

    conn.commit()

    return conn


def initialize_database():
    """Initialize user database tables without keeping a connection open."""

    conn = get_connection()
    conn.close()
