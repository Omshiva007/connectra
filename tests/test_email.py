"""
Tests for email logging (connectra_core.email_sender.log_email).
SMTP sending is fully mocked to avoid requiring a real Gmail account.
"""
from unittest.mock import patch, MagicMock
import pytest


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
            body="<p>Hello</p>",
        )

        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@example.com", "app_pass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()
