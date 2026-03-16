from datetime import datetime
import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


RUNTIME_ROOT = os.environ.get("CONNECTRA_RUNTIME_ROOT", "C:/Connectra")
DATA_DIR = os.path.join(RUNTIME_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "connectra_central.db")


def ensure_runtime():
    if not os.path.exists(RUNTIME_ROOT):
        os.mkdir(RUNTIME_ROOT)

    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)


def get_connection():
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

    conn.commit()
    return conn


class EmailLog(BaseModel):
    timestamp: datetime
    user_email: str
    client_domain: str
    template_name: str
    recipient_count: int


app = FastAPI(title="Connectra Central Backend")


@app.post("/logs/email")
def create_email_log(payload: EmailLog):
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

