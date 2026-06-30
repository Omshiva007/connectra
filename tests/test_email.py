"""
Tests for email logging (connectra_core.email_sender.log_email).
SMTP sending is fully mocked to avoid requiring a real Gmail account.
"""
from unittest.mock import patch, MagicMock
from email import message_from_string
import pytest
import smtplib


def _message_parts(raw_message, content_type):
    """Return decoded MIME part payloads for a content type."""
    message = message_from_string(raw_message)
    parts = []
    for part in message.walk():
        if part.get_content_type() == content_type:
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            parts.append(payload.decode(charset))
    return parts


def test_log_email_writes_to_db(isolated_data_dir):
    """log_email must insert a row into the email_logs table."""
    from connectra_core.email_sender import log_email
    from connectra_core.database import get_connection

    log_email(
        user_email="sender@example.com",
        domain="client.com",
        template_name="Welcome",
        recipient_count=3,
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM email_logs")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


def test_log_email_records_correct_values(isolated_data_dir):
    """log_email must persist the correct field values."""
    from connectra_core.email_sender import log_email
    from connectra_core.database import get_connection

    log_email(
        user_email="admin@myco.com",
        domain="partner.com",
        template_name="Holiday Greeting",
        recipient_count=10,
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_email, client_domain, template_name, recipient_count "
        "FROM email_logs"
    )
    row = cursor.fetchone()
    conn.close()

    assert row[0] == "admin@myco.com"
    assert row[1] == "partner.com"
    assert row[2] == "Holiday Greeting"
    assert row[3] == 10


def test_send_email_calls_smtp(isolated_data_dir):
    """send_email must use SMTP with TLS and call sendmail."""
    from connectra_core.email_sender import send_email

    with patch("connectra_core.email_sender.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        send_email(
            user_email="sender@example.com",
            password="app_pass",
            recipients=["alice@example.com", "bob@example.com"],
            subject="Test Subject",
            body="Hello\n\nRegards,\nTeam",
        )

        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "app_pass")
        mock_server.sendmail.assert_called_once()
        sent_message = mock_server.sendmail.call_args.args[2]
        assert "<p>Hello</p><p>Regards,<br>Team</p>" in _message_parts(sent_message, "text/html")[0]
        mock_server.quit.assert_called_once()


def test_send_email_uses_admin_mail_settings(isolated_data_dir):
    """Admin mailbox settings should control SMTP host, port, and TLS."""
    from connectra_core.admin_database import set_setting
    from connectra_core.email_sender import send_email

    set_setting("smtp_server", "smtp.office365.com")
    set_setting("smtp_port", "2525")
    set_setting("smtp_use_tls", "0")

    with patch("connectra_core.email_sender.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        send_email(
            user_email="sender@example.com",
            password="app_pass",
            recipients=["alice@example.com"],
            subject="Test Subject",
            body="<p>Hello</p>",
        )

        mock_smtp_cls.assert_called_once_with("smtp.office365.com", 2525, timeout=30)
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_called_once_with("sender@example.com", "app_pass")


def test_send_email_embeds_html_data_images_as_inline_parts(isolated_data_dir):
    """Data URI images in template HTML should become inline MIME image parts."""
    from connectra_core.email_sender import send_email

    image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    html_body = f'<p>Hello</p><img src="data:image/png;base64,{image_data}">'

    with patch("connectra_core.email_sender.smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        send_email(
            user_email="sender@example.com",
            password="app_pass",
            recipients=["alice@example.com"],
            subject="Image Subject",
            plain_body="Hello",
            html_body=html_body,
        )

        sent_message = mock_server.sendmail.call_args.args[2]
        html_part = _message_parts(sent_message, "text/html")[0]
        assert "Content-Type: image/png" in sent_message
        assert "Content-ID: <connectra-image-" in sent_message
        assert "src=\"cid:connectra-image-" in html_part
        assert "data:image/png;base64" not in html_part


def test_send_email_raises_user_friendly_error(isolated_data_dir):
    """SMTP failures should surface as product-level send errors."""
    from connectra_core.email_sender import EmailSendError, send_email

    with patch("connectra_core.email_sender.smtplib.SMTP") as mock_smtp_cls:
        mock_smtp_cls.side_effect = smtplib.SMTPException("bad credentials")

        with pytest.raises(EmailSendError):
            send_email(
                user_email="sender@example.com",
                password="bad_pass",
                recipients=["alice@example.com"],
                subject="Test Subject",
                body="<p>Hello</p>",
            )


def test_scan_mailbox_reports_progress_and_summary(isolated_data_dir):
    """Mailbox scan should report visible stages and return summary counts."""
    from connectra_core.email_scanner import scan_mailbox

    mock_mail = MagicMock()
    mock_mail.search.return_value = ("OK", [b"1"])
    mock_mail.fetch.return_value = (
        "OK",
        [
            (
                b"1",
                b"To: Friend <friend@client.com>\r\nCc: Internal <me@example.com>\r\n\r\n",
            )
        ],
    )

    progress_events = []

    with patch("connectra_core.email_scanner.imaplib.IMAP4_SSL", return_value=mock_mail):
        summary = scan_mailbox(
            "me@example.com",
            "app-pass",
            "example.com",
            30,
            lambda message, current=None, total=None: progress_events.append(
                (message, current, total)
            ),
        )

    assert summary == {
        "messages_scanned": 1,
        "contacts_found": 1,
        "domains_found": 1,
    }
    assert progress_events[0][0] == "Connecting to mailbox server..."
    assert any(event[0].startswith("Scanning headers") for event in progress_events)
    assert progress_events[-1][0] == "Scan completed"


def test_scan_mailbox_reports_missing_ssl_support(isolated_data_dir, monkeypatch):
    """Packaged builds without SSL should fail with a clear scan error."""
    import imaplib

    from connectra_core.email_scanner import MailboxScanError, scan_mailbox

    monkeypatch.delattr(imaplib, "IMAP4_SSL", raising=False)

    with pytest.raises(MailboxScanError, match="SSL support"):
        scan_mailbox("me@example.com", "app-pass", "example.com", 30)
