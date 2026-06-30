"""Admin activity reporting helpers for local outreach logs."""

import sqlite3
import csv

from connectra_core.config import DATA_DIR

USER_DB = DATA_DIR / "connectra_user.db"


def get_logs():
    """Read user-app outreach activity from the shared local user database."""
    if not USER_DB.exists():
        return []

    conn = sqlite3.connect(str(USER_DB))
    cursor = conn.cursor()

    try:

        cursor.execute("""
        SELECT timestamp,user_email,client_domain,template_name,recipient_count
        FROM email_logs
        ORDER BY timestamp DESC
        """)

        rows = cursor.fetchall()

    except sqlite3.Error:
        rows = []

    conn.close()

    return rows


def get_activity_summary():
    """Aggregate local activity rows for the admin dashboard counters."""
    logs = get_logs()
    users = {row[1] for row in logs}
    clients = {row[2] for row in logs}
    recipients = sum(row[4] or 0 for row in logs)

    return {
        "emails_sent": len(logs),
        "active_users": len(users),
        "client_domains": len(clients),
        "recipients": recipients,
    }


def export_logs_csv(output_path):
    """Export activity rows to CSV for offline reporting or sharing."""
    logs = get_logs()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "User", "Client", "Template", "Recipients"])
        writer.writerows(logs)

    return len(logs)
