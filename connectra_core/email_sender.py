"""SMTP sending and outreach activity logging helpers."""

import smtplib
import base64
import re
import uuid
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import json
import urllib.error
import urllib.request

from connectra_core.database import get_connection
from connectra_core.config import BACKEND_BASE_URL
from connectra_core.mail_settings import get_mail_settings
from connectra_core.template_renderer import render_template_html

_DATA_IMAGE_RE = re.compile(
    r'src=["\']data:(image/[a-zA-Z0-9.+-]+);base64,([^"\']+)["\']',
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class EmailSendError(RuntimeError):
    """Raised when SMTP sending fails with a user-facing cause."""


def _plain_from_html(html_body: str) -> str:
    """Create a readable plain-text fallback from HTML content."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", html_body)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = _HTML_TAG_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _build_message(user_email, recipients, subject, plain_body, html_body):
    """Build a multipart email with optional inline data-image attachments."""
    image_parts = []

    def replace_data_image(match):
        mime_type = match.group(1)
        image_bytes = base64.b64decode(match.group(2))
        content_id = f"connectra-image-{uuid.uuid4().hex}"
        image_part = MIMEImage(image_bytes, _subtype=mime_type.split("/", 1)[1])
        image_part.add_header("Content-ID", f"<{content_id}>")
        image_part.add_header("Content-Disposition", "inline", filename=f"{content_id}")
        image_parts.append(image_part)
        return f'src="cid:{content_id}"'

    html_with_cids = _DATA_IMAGE_RE.sub(replace_data_image, html_body)
    plain_text = plain_body.strip() or _plain_from_html(html_with_cids)

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = user_email
    msg["To"] = recipients[0]

    if len(recipients) > 1:
        msg["Cc"] = ", ".join(recipients[1:])

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_text, "plain", "utf-8"))
    alternative.attach(MIMEText(html_with_cids, "html", "utf-8"))
    msg.attach(alternative)

    for image_part in image_parts:
        msg.attach(image_part)

    return msg


def _send_log_to_backend(timestamp, user_email, domain, template_name, recipient_count):
    """Best-effort central activity sync; local logs remain source of truth."""

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
    """Persist local outreach activity and attempt central reporting sync."""

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


def send_email(user_email, password, recipients, subject, body="", plain_body="", html_body=""):
    """Send template HTML through the user's configured mailbox account."""
    settings = get_mail_settings()

    server = None

    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30)
        if settings.use_tls:
            server.starttls()

        server.login(user_email, password)

        rendered_html = render_template_html(plain_body, html_body, body)
        msg = _build_message(user_email, recipients, subject, plain_body or body, rendered_html)

        server.sendmail(
            user_email,
            recipients,
            msg.as_string()
        )
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(
            "Email could not be sent. Check SMTP settings, app password, recipients, and network access."
        ) from exc
    finally:
        if server is not None:
            try:
                server.quit()
            except smtplib.SMTPException:
                pass
