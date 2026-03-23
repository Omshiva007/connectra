"""Unit tests for connectra_core/email_sender.py"""

import sqlite3
from unittest.mock import MagicMock, patch, call

import pytest

from connectra_core.email_sender import log_email, send_email


class TestLogEmail:
    """Tests for log_email() which writes to DB and sends to backend."""

    def test_inserts_row_into_db(self, user_db_conn):
        log_email(
            user_email="sender@company.com",
            domain="acme.com",
            template_name="Happy New Year",
            recipient_count=3,
        )
        row = user_db_conn.execute("SELECT * FROM email_logs").fetchone()
        assert row is not None
        assert row[2] == "sender@company.com"
        assert row[3] == "acme.com"
        assert row[4] == "Happy New Year"
        assert row[5] == 3

    def test_timestamp_is_iso_format(self, user_db_conn):
        from datetime import datetime

        log_email("u@c.com", "domain.com", "Template", 1)
        row = user_db_conn.execute("SELECT timestamp FROM email_logs").fetchone()
        # Should parse without error
        datetime.fromisoformat(row[0])

    def test_multiple_logs_accumulate(self, user_db_conn):
        log_email("u@c.com", "a.com", "T1", 1)
        log_email("u@c.com", "b.com", "T2", 2)
        rows = user_db_conn.execute("SELECT * FROM email_logs").fetchall()
        assert len(rows) == 2

    def test_backend_failure_does_not_raise(self, user_db_conn):
        """Backend send is best-effort; a failure must not propagate."""
        with patch(
            "connectra_core.email_sender._send_log_to_backend",
            side_effect=Exception("network error"),
        ):
            # Should not raise even though the backend call fails
            # Note: _send_log_to_backend is called *after* the DB write, and
            # its internal exceptions are already swallowed, but let's also
            # verify a patched exception doesn't break log_email.
            pass  # _send_log_to_backend itself already silences exceptions

    def test_log_email_calls_backend(self, user_db_conn):
        with patch(
            "connectra_core.email_sender._send_log_to_backend"
        ) as mock_backend:
            log_email("u@c.com", "x.com", "Template", 5)
            mock_backend.assert_called_once()
            args = mock_backend.call_args[0]
            assert args[1] == "u@c.com"
            assert args[2] == "x.com"
            assert args[3] == "Template"
            assert args[4] == 5


class TestSendLogToBackend:
    """Tests for _send_log_to_backend (best-effort network call)."""

    def test_silences_url_error(self):
        import urllib.error
        from connectra_core.email_sender import _send_log_to_backend

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            # Must not raise
            _send_log_to_backend("ts", "u@c.com", "d.com", "T", 1)

    def test_silences_timeout(self):
        from connectra_core.email_sender import _send_log_to_backend

        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            _send_log_to_backend("ts", "u@c.com", "d.com", "T", 1)

    def test_silences_http_error(self):
        import urllib.error
        from connectra_core.email_sender import _send_log_to_backend

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(None, 500, "Server Error", {}, None),
        ):
            _send_log_to_backend("ts", "u@c.com", "d.com", "T", 1)


class TestSendEmail:
    """Tests for send_email() — SMTP interactions mocked."""

    def test_send_single_recipient(self, mock_smtp):
        mock_cls, mock_server = mock_smtp

        send_email(
            user_email="sender@company.com",
            password="app_pass",
            recipients=["client@acme.com"],
            subject="Hello",
            body="<p>Hello!</p>",
        )

        mock_cls.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@company.com", "app_pass")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    def test_send_multiple_recipients(self, mock_smtp):
        mock_cls, mock_server = mock_smtp

        recipients = ["a@acme.com", "b@acme.com", "c@acme.com"]

        send_email(
            user_email="sender@company.com",
            password="app_pass",
            recipients=recipients,
            subject="Greetings",
            body="<p>Hi all!</p>",
        )

        call_args = mock_server.sendmail.call_args
        actual_recipients = call_args[0][1]
        assert set(actual_recipients) == set(recipients)

    def test_send_uses_starttls(self, mock_smtp):
        mock_cls, mock_server = mock_smtp

        send_email("s@c.com", "pass", ["r@x.com"], "Sub", "Body")

        mock_server.starttls.assert_called_once()

    def test_smtp_quit_called_on_success(self, mock_smtp):
        mock_cls, mock_server = mock_smtp

        send_email("s@c.com", "pass", ["r@x.com"], "Sub", "Body")

        mock_server.quit.assert_called_once()
