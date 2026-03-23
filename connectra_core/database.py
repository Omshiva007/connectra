import sqlite3
import os
from pathlib import Path

RUNTIME_ROOT = Path(os.environ.get("CONNECTRA_HOME", Path.home() / ".connectra"))
DATA_DIR = RUNTIME_ROOT / "data"
DB_NAME = DATA_DIR / "connectra_user.db"


def ensure_runtime():

    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():

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

    conn = get_connection()
    conn.close()