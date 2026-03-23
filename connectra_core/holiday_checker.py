import sqlite3
from datetime import datetime, timedelta

from connectra_core.config import DATA_DIR

ADMIN_DB = DATA_DIR / "connectra_admin.db"


def get_connection():
    return sqlite3.connect(str(ADMIN_DB))


def check_upcoming_holidays():

    if not ADMIN_DB.exists():
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
        raw_date = row[1]
        template = row[2]
        reminder_days = row[3]

        if not raw_date:
            continue

        parsed_date = None

        # try strict YYYY-MM-DD first
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except (TypeError, ValueError):
                continue

        if parsed_date is None:
            # last resort: try generic parse like 'January 26, 2026'
            try:
                parsed_date = datetime.strptime(raw_date, "%B %d, %Y").date()
            except (TypeError, ValueError):
                # skip bad rows instead of crashing
                continue

        date = parsed_date

        reminder_date = date - timedelta(days=reminder_days)

        if today == reminder_date:

            upcoming.append({
                "holiday": holiday,
                "template": template,
                "date": date
            })

    return upcoming