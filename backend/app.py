"""Small central/HQ API for reporting and admin-approved rollout metadata."""

from datetime import datetime
import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


RUNTIME_ROOT = os.environ.get("CONNECTRA_RUNTIME_ROOT", "C:/Connectra")
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "connectra_central.db")


def ensure_runtime():
    """Create the central backend data folders on first run."""
    if not os.path.exists(RUNTIME_ROOT):
        os.mkdir(RUNTIME_ROOT)

    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)


def get_connection():
    """Open the central SQLite database and ensure backend tables exist."""
    ensure_runtime()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_email TEXT,
            client_domain TEXT,
            template_name TEXT,
            recipient_count INTEGER
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rollout_settings(
            id INTEGER PRIMARY KEY CHECK (id = 1),
            available_version TEXT,
            approved_version TEXT,
            installer_url TEXT,
            release_notes TEXT,
            updated_at TEXT
        )
        """
    )

    conn.commit()
    return conn


class EmailLog(BaseModel):
    """Audit record sent by user apps after template-based outreach."""

    timestamp: datetime
    user_email: str
    client_domain: str
    template_name: str
    recipient_count: int


class RolloutSettings(BaseModel):
    """Version metadata approved by admin before users see update notices."""

    available_version: str = ""
    approved_version: str = ""
    installer_url: str = ""
    release_notes: str = ""


app = FastAPI(title="Connectra Central Backend")


@app.post("/logs/email")
def create_email_log(payload: EmailLog):
    """Persist a single outreach activity record for central reporting."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO email_logs(timestamp,user_email,client_domain,template_name,recipient_count)
            VALUES(?,?,?,?,?)
            """,
            (
                payload.timestamp.isoformat(),
                payload.user_email,
                payload.client_domain,
                payload.template_name,
                payload.recipient_count,
            ),
        )

        conn.commit()
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {"status": "ok"}


@app.get("/logs/email")
def list_email_logs():
    """Return all outreach activity rows in reverse chronological order."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT timestamp,user_email,client_domain,template_name,recipient_count
        FROM email_logs
        ORDER BY timestamp DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "timestamp": row[0],
            "user_email": row[1],
            "client_domain": row[2],
            "template_name": row[3],
            "recipient_count": row[4],
        }
        for row in rows
    ]


@app.get("/reports/summary")
def report_summary():
    """Aggregate high-level adoption metrics for the future HQ dashboard."""
    rows = list_email_logs()
    users = {row["user_email"] for row in rows}
    clients = {row["client_domain"] for row in rows}
    templates = {row["template_name"] for row in rows}

    return {
        "emails_sent": len(rows),
        "active_users": len(users),
        "client_domains": len(clients),
        "templates_used": len(templates),
        "recipients": sum(row["recipient_count"] or 0 for row in rows),
    }


@app.get("/rollout")
def get_rollout_settings():
    """Return the currently approved rollout metadata."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT available_version,approved_version,installer_url,release_notes,updated_at
        FROM rollout_settings
        WHERE id=1
        """
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "available_version": "",
            "approved_version": "",
            "installer_url": "",
            "release_notes": "",
            "updated_at": "",
        }

    return {
        "available_version": row[0],
        "approved_version": row[1],
        "installer_url": row[2],
        "release_notes": row[3],
        "updated_at": row[4],
    }


@app.put("/rollout")
def update_rollout_settings(payload: RolloutSettings):
    """Save admin-reviewed version metadata for controlled rollout."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO rollout_settings(
            id,available_version,approved_version,installer_url,release_notes,updated_at
        )
        VALUES(1,?,?,?,?,?)
        """,
        (
            payload.available_version,
            payload.approved_version,
            payload.installer_url,
            payload.release_notes,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

