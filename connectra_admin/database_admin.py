import sqlite3
import os

RUNTIME_ROOT = "C:/Connectra"
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
DB_NAME = os.path.join(DATA_DIR, "connectra_admin.db")


def ensure_runtime():

    if not os.path.exists(RUNTIME_ROOT):
        os.mkdir(RUNTIME_ROOT)

    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)


def get_connection():

    ensure_runtime()

    conn = sqlite3.connect(DB_NAME)
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
        (email, password)
    )

    conn.commit()
    conn.close()