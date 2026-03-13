import sqlite3
from datetime import datetime, timedelta
import os

RUNTIME_ROOT = "C:/Connectra"
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")

ADMIN_DB = os.path.join(DATA_DIR, "connectra_admin.db")


def get_connection():
    return sqlite3.connect(ADMIN_DB)


def check_upcoming_holidays():

    if not os.path.exists(ADMIN_DB):
        return []

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT holiday,date,template,reminder_days
    FROM holiday_calendar
    WHERE active=1
    """)

    rows = cursor.fetchall()

    conn.close()

    today = datetime.today().date()

    upcoming = []

    for row in rows:

        holiday = row[0]
        date = datetime.strptime(row[1], "%Y-%m-%d").date()
        template = row[2]
        reminder_days = row[3]

        reminder_date = date - timedelta(days=reminder_days)

        if today == reminder_date:

            upcoming.append({
                "holiday": holiday,
                "template": template,
                "date": date
            })

    return upcoming