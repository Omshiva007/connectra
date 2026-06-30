"""
Read-only access helpers for the shared admin database (connectra_admin.db).

This module is used by the User App to read admin-managed data such as user
credentials, settings, and holiday information without depending on the Admin
App's internal package directly.
"""
import sqlite3

from connectra_core.config import DATA_DIR
from connectra_core.security import encrypt_password, decrypt_password

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = DATA_DIR / "connectra_admin.db"


def get_connection():
    """Open the shared admin database and ensure expected tables exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_NAME))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holiday_calendar(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holiday TEXT,
        date TEXT,
        region TEXT,
        template TEXT,
        reminder_days INTEGER,
        active INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE,
        email TEXT UNIQUE,
        login_passcode TEXT,
        app_password TEXT,
        active INTEGER
    )
    """)
    _ensure_user_columns(cursor)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )
    """)

    conn.commit()
    return conn


def _ensure_user_columns(cursor):
    """Add newer user columns to existing shared admin databases."""
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if "login_passcode" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN login_passcode TEXT")
    if "employee_id" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN employee_id TEXT")


def get_setting(key):
    """Return one shared setting value or None when it is unset."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def add_user(employee_id, email, login_passcode):
    """Create or replace a licensed user bootstrap identity."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO users(employee_id, email, login_passcode, active)
        VALUES(?, ?, ?, 1)
        """,
        (employee_id, email, encrypt_password(login_passcode)),
    )
    conn.commit()
    conn.close()


def get_user_password(email):
    """Return the plaintext app password for *email*, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT app_password FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return decrypt_password(row[0])
        except ValueError:
            return row[0]
    return None


def get_user_login_passcode(email):
    """Return the plaintext User App login passcode for *email*."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT login_passcode FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return decrypt_password(row[0])
        except ValueError:
            return row[0]
    return None


def get_user_employee_id(email):
    """Return the employee ID for *email*, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return None


def update_user(original_email, employee_id, email, login_passcode):
    """Update a user's employee ID, email, and login passcode."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET employee_id=?, email=?, login_passcode=?
        WHERE email=?
        """,
        (
            employee_id,
            email,
            encrypt_password(login_passcode),
            original_email,
        ),
    )
    conn.commit()
    updated_count = cursor.rowcount
    conn.close()
    return updated_count


def delete_user(email):
    """Delete a configured user and their encrypted app password."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email=?", (email,))
    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()
    return deleted_count


def user_exists(email):
    """Return True when a configured user exists for the given email."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_all_users():
    """Return configured users without exposing encrypted passwords."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, email, active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows


def set_setting(key, value):
    """Create or replace a shared setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()
