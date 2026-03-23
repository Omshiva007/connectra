import sqlite3

from connectra_core.config import DATA_DIR
from connectra_core.security import encrypt_password, decrypt_password

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_NAME = DATA_DIR / "connectra_admin.db"


def ensure_runtime():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():

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
        email TEXT UNIQUE,
        app_password TEXT,
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


def initialize_admin_database():

    conn = get_connection()
    conn.close()


def get_holidays():

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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email,active FROM users")

    rows = cursor.fetchall()

    conn.close()

    return rows


def add_user(email, password):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO users(email,app_password,active) VALUES(?,?,1)",
        (email, encrypt_password(password))
    )

    conn.commit()
    conn.close()


def get_setting(key):

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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (key, value),
    )

    conn.commit()
    conn.close()