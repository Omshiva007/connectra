import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import json
import urllib.error
import urllib.request

from connectra_core.database import get_connection
from connectra_core.config import BACKEND_BASE_URL


def _send_log_to_backend(timestamp, user_email, domain, template_name, recipient_count):

    try:
        url = f"{BACKEND_BASE_URL.rstrip('/')}/logs/email"

        payload = {
            "timestamp": timestamp,
            "user_email": user_email,
            "client_domain": domain,
            "template_name": template_name,
            "recipient_count": recipient_count
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=5):
            pass

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        # Best-effort only: ignore failures
        return


def log_email(user_email, domain, template_name, recipient_count):

    timestamp = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO email_logs(timestamp,user_email,client_domain,template_name,recipient_count)
        VALUES(?,?,?,?,?)
    """, (
        timestamp,
        user_email,
        domain,
        template_name,
        recipient_count
    ))

    conn.commit()
    conn.close()

    _send_log_to_backend(
        timestamp,
        user_email,
        domain,
        template_name,
        recipient_count
    )


def send_email(user_email, password, recipients, subject, body):

    smtp_server = "smtp.gmail.com"
    port = 587

    server = smtplib.SMTP(smtp_server, port)
    server.starttls()

    server.login(user_email, password)

    msg = MIMEText(body, "html")

    msg["Subject"] = subject
    msg["From"] = user_email
    msg["To"] = recipients[0]

    if len(recipients) > 1:
        msg["Cc"] = ", ".join(recipients[1:])

    server.sendmail(
        user_email,
        recipients,
        msg.as_string()
    )

    server.quit()