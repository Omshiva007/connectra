import sqlite3


def get_connection():
    return sqlite3.connect("app.db")


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_config(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

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

    conn.commit()
    conn.close()


def get_config(key):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT value FROM app_config WHERE key=?",
        (key,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]

    return None