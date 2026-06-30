"""Admin desktop database helpers for users, holidays, and shared settings."""

import sqlite3

from connectra_core.config import DATA_DIR
from connectra_core.security import encrypt_password, decrypt_password

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = DATA_DIR / "connectra_admin.db"


def ensure_runtime():
    """Create the configured data directory before opening SQLite files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Open the admin SQLite database and ensure all admin tables exist."""

    ensure_runtime()

    conn = sqlite3.connect(str(DB_NAME))
    cursor = conn.cursor()

    # holiday calendar table
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

    # admin users
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

    # admin login accounts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        active INTEGER
    )
    """)

    # settings (for logo, theme, etc.)
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
    """Add newer user columns to existing admin databases."""
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if "login_passcode" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN login_passcode TEXT")
    if "employee_id" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN employee_id TEXT")


def initialize_admin_database():
    """Initialize admin database tables without keeping a connection open."""

    conn = get_connection()
    conn.close()


def get_admin_accounts():
    """Return configured Admin login emails and active flags."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email,active FROM admin_accounts")

    rows = cursor.fetchall()

    conn.close()

    return rows


def add_admin_account(email, password):
    """Create or replace an Admin login account with an encrypted password."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO admin_accounts(email,password,active) VALUES(?,?,1)",
        (email, encrypt_password(password)),
    )

    conn.commit()
    conn.close()


def verify_admin_login(email, password):
    """Return True when the Admin email/password match a saved account."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT password FROM admin_accounts WHERE email=? AND active=1",
        (email,),
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    try:
        expected_password = decrypt_password(row[0])
    except ValueError:
        expected_password = row[0]

    return expected_password == password


def get_holidays():
    """Return configured holiday reminders for the Admin app table."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT holiday,date,region,template,reminder_days,active
    FROM holiday_calendar
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_users():
    """Return configured users with saved-credential status for the table."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COALESCE(employee_id, ''),
        email,
        CASE WHEN login_passcode IS NULL OR login_passcode='' THEN 'Missing' ELSE 'Saved' END,
        active
    FROM users
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def add_user(employee_id, email, login_passcode):
    """Create or replace a user bootstrap identity."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO users(employee_id,email,login_passcode,active)
        VALUES(?,?,?,1)
        """,
        (employee_id, email, encrypt_password(login_passcode))
    )

    conn.commit()
    conn.close()


def update_user(original_email, employee_id, email, login_passcode):
    """Update a user's bootstrap identity."""

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
        )
    )

    conn.commit()
    conn.close()


def delete_user(email):
    """Delete a configured user and their encrypted app password."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE email=?", (email,))

    conn.commit()
    deleted_count = cursor.rowcount
    conn.close()

    return deleted_count


def get_user_password(email):
    """Return the plaintext app password for *email*, or None if not found."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT app_password FROM users WHERE email=?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            return decrypt_password(row[0])
        except ValueError:
            # Fallback for passwords stored before encryption was introduced.
            return row[0]

    return None


def get_user_employee_id(email):
    """Return the employee ID for *email*, or None if not found."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT employee_id FROM users WHERE email=?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row and row[0]:
        return row[0]

    return None


def get_user_login_passcode(email):
    """Return the plaintext User App login passcode for *email*."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT login_passcode FROM users WHERE email=?",
        (email,)
    )

    row = cursor.fetchone()
    conn.close()

    if row and row[0]:
        try:
            return decrypt_password(row[0])
        except ValueError:
            return row[0]

    return None


def get_setting(key):
    """Read one admin setting value, returning None when it is unset."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]

    return None


def set_setting(key, value):
    """Create or replace a shared admin setting value."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (key, value),
    )

    conn.commit()
    conn.close()
