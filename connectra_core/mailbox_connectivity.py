"""Connectivity checks for user-supplied mailbox app keys."""

import imaplib
import smtplib
import socket

from connectra_core.mail_settings import get_mail_settings


class MailboxConnectivityError(RuntimeError):
    """Raised when a mailbox key cannot connect to IMAP or SMTP."""


def test_mailbox_connectivity(email: str, mailbox_key: str) -> None:
    """Validate that a mailbox key can authenticate to IMAP and SMTP."""
    settings = get_mail_settings()

    try:
        if not hasattr(imaplib, "IMAP4_SSL"):
            raise MailboxConnectivityError(
                "Secure mailbox scanning is unavailable in this build."
            )

        imap_server = imaplib.IMAP4_SSL(settings.imap_server)
        try:
            imap_server.login(email, mailbox_key)
            imap_server.select("inbox", readonly=True)
        finally:
            try:
                imap_server.logout()
            except imaplib.IMAP4.error:
                pass

        smtp_server = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=30)
        try:
            if settings.use_tls:
                smtp_server.starttls()
            smtp_server.login(email, mailbox_key)
        finally:
            try:
                smtp_server.quit()
            except smtplib.SMTPException:
                pass
    except MailboxConnectivityError:
        raise
    except imaplib.IMAP4.error as exc:
        raise MailboxConnectivityError(
            "Mailbox key could not authenticate to IMAP. Check app key and IMAP access."
        ) from exc
    except smtplib.SMTPException as exc:
        raise MailboxConnectivityError(
            "Mailbox key could not authenticate to SMTP. Check app key and SMTP settings."
        ) from exc
    except (OSError, socket.timeout) as exc:
        raise MailboxConnectivityError(
            "Could not connect to mailbox servers. Check network and provider settings."
        ) from exc
