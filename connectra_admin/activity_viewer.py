import sqlite3
import os

RUNTIME_ROOT = "C:/Connectra"
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
USER_DB = os.path.join(DATA_DIR, "connectra_user.db")


def get_logs():

    if not os.path.exists(USER_DB):
        return []

    conn = sqlite3.connect(USER_DB)
    cursor = conn.cursor()

    try:

        cursor.execute("""
        SELECT timestamp,user_email,client_domain,template_name,recipient_count
        FROM email_logs
        ORDER BY timestamp DESC
        """)

        rows = cursor.fetchall()

    except:
        rows = []

    conn.close()

    return rows