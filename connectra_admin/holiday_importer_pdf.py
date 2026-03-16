import re
from datetime import datetime

from database_admin import get_connection


LINE_PATTERN = re.compile(
    r"^\s*\d+\s+(.+?)\s+([A-Za-z]+ \d{1,2}, [A-Za-z]+, \d{4})\s*$"
)


def parse_pdf_text(lines):
    holidays = []

    for line in lines:
        line = line.strip()

        match = LINE_PATTERN.match(line)
        if not match:
            continue

        name = match.group(1).strip()
        raw_date = match.group(2).strip()

        # examples: "January 26, Monday, 2026"
        #          "November 08, Sunday, 2026"
        parts = raw_date.split(",")
        if len(parts) < 3:
            continue

        date_part = parts[0].strip()  # "January 26" or "November 08"
        year_part = parts[-1].strip()  # "2026"

        unified = f"{date_part}, {year_part}"  # "January 26, 2026"

        try:
            d = datetime.strptime(unified, "%B %d, %Y").date()
        except ValueError:
            continue

        holidays.append((name, d))

    return holidays


def import_holiday_pdf_lines(lines):
    holidays = parse_pdf_text(lines)

    if not holidays:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM holiday_calendar")

    for holiday, d in holidays:
        cursor.execute(
            """
            INSERT INTO holiday_calendar
            (holiday,date,region,template,reminder_days,active)
            VALUES (?,?,?,?,?,?)
            """,
            (
                holiday,
                d.strftime("%Y-%m-%d"),
                "India",
                "Holiday Greeting",
                7,
                1,
            ),
        )

    conn.commit()
    conn.close()

