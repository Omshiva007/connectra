from datetime import date

from database_admin import get_connection


HOLIDAYS_2026 = [
    # (holiday, date(YYYY, M, D))
    ("Republic Day", date(2026, 1, 26)),
    ("Doljatra", date(2026, 3, 3)),
    ("Eid-al-Fitr", date(2026, 3, 20)),
    ("May Day", date(2026, 5, 1)),
    ("Independence Day", date(2026, 8, 15)),
    ("Gandhi Jayanti", date(2026, 10, 2)),
    ("Durga Puja-Saptami", date(2026, 10, 18)),
    ("Durga Puja-Ashtami", date(2026, 10, 19)),
    ("Durga Puja-Nabami", date(2026, 10, 20)),
    ("Durga Puja-Dashami", date(2026, 10, 21)),
    ("Diwali / Kali Puja", date(2026, 11, 8)),
    ("Christmas Day", date(2026, 12, 25)),
    ("New Year's Day", date(2027, 1, 1)),
]


def seed():
    conn = get_connection()
    cursor = conn.cursor()

    for holiday, d in HOLIDAYS_2026:
        cursor.execute(
            """
            INSERT OR REPLACE INTO holiday_calendar(holiday,date,region,template,reminder_days,active)
            VALUES(?,?,?,?,?,1)
            """,
            (
                holiday,
                d.strftime("%Y-%m-%d"),
                "India",
                "Holiday Greeting",
                7,
            ),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
    print("Seeded 2026 holidays into holiday_calendar.")

