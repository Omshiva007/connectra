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
        email TEXT UNIQUE,
        app_password TEXT,
        active INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )
    """)

    conn.commit()
    return conn


def get_setting(key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def add_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users(email, app_password, active) VALUES(?, ?, 1)",
        (email, encrypt_password(password)),
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


def user_exists(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE email=?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows


def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()
