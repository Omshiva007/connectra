import os
import sqlite3

RUNTIME_ROOT = "C:/Connectra"
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
ADMIN_DB = os.path.join(DATA_DIR, "connectra_admin.db")


def ensure_runtime():
    if not os.path.exists(RUNTIME_ROOT):
        os.mkdir(RUNTIME_ROOT)

    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)


def get_connection():
    ensure_runtime()

    conn = sqlite3.connect(ADMIN_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            app_password TEXT,
            active INTEGER DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
        """
    )

    conn.commit()
    return conn


def get_setting(key: str) -> str | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return None


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
        (key, value),
    )

    conn.commit()
    conn.close()
