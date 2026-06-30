"""Mailbox header scanner for discovering external To/CC contacts."""

import imaplib
import email
import socket
from datetime import datetime, timedelta

from connectra_core.database import get_connection
from connectra_core.filters import is_internal_email
from connectra_core.mail_settings import get_mail_settings


class MailboxScanError(RuntimeError):
    """Raised when mailbox scanning cannot complete with a user-facing cause."""


def scan_mailbox(email_user, password, internal_domain, days, progress_callback=None):
    """Scan mailbox headers and store external To/CC contacts by domain.

    MVP privacy boundary: only headers are fetched, and only recipient fields
    are parsed. Email bodies are never requested from the IMAP server.
    """
    mail = None

    try:
        settings = get_mail_settings()
        if not hasattr(imaplib, "IMAP4_SSL"):
            raise MailboxScanError(
                "Secure mailbox scanning is unavailable in this build. "
                "Ask admin to rebuild the User app with SSL support."
            )

        _emit_scan_progress(progress_callback, "Connecting to mailbox server...")
        mail = imaplib.IMAP4_SSL(settings.imap_server)
        _emit_scan_progress(progress_callback, "Authenticating mailbox...")
        mail.login(email_user, password)

        _emit_scan_progress(progress_callback, "Opening inbox...")
        mail.select("inbox", readonly=True)

        _emit_scan_progress(progress_callback, "Searching messages...")
        if days:
            since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, data = mail.search(None, f'(SINCE "{since_date}")')
        else:
            status, data = mail.search(None, "ALL")

        if status != "OK" or not data:
            return {"messages_scanned": 0, "contacts_found": 0, "domains_found": 0}

        mail_ids = data[0].split()
        total = len(mail_ids)
        _emit_scan_progress(progress_callback, f"Found {total} messages to scan", 0, total)

        conn = get_connection()
        cursor = conn.cursor()

        # reset current discovery so filters apply fresh on each scan
        cursor.execute("DELETE FROM contacts")
        cursor.execute("DELETE FROM clients")

        for index, num in enumerate(mail_ids):
            # BODY.PEEK[HEADER] avoids marking messages read and avoids body access.
            status, msg_data = mail.fetch(num, "(BODY.PEEK[HEADER])")
            if status != "OK" or not msg_data:
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            fields = ["to", "cc"]

            for field in fields:
                value = msg.get(field)

                if not value:
                    continue

                addresses = email.utils.getaddresses([value])

                for name, addr in addresses:
                    addr = addr.lower()

                    if is_internal_email(addr, internal_domain):
                        continue

                    domain = addr.split("@")[-1]

                    cursor.execute(
                        "INSERT OR IGNORE INTO clients(domain) VALUES(?)",
                        (domain,)
                    )

                    cursor.execute(
                        "INSERT OR IGNORE INTO contacts(email,domain) VALUES(?,?)",
                        (addr, domain)
                    )

            if progress_callback:
                _emit_scan_progress(
                    progress_callback,
                    f"Scanning headers {index + 1}/{total}",
                    index + 1,
                    total,
                )

        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM contacts")
        contacts_found = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clients")
        domains_found = cursor.fetchone()[0]
        conn.close()

        _emit_scan_progress(progress_callback, "Scan completed", total, total)
        return {
            "messages_scanned": total,
            "contacts_found": contacts_found,
            "domains_found": domains_found,
        }

    except imaplib.IMAP4.error as exc:
        raise MailboxScanError(
            "Mailbox login or scan failed. Check the email, app password, IMAP access, and provider settings."
        ) from exc
    except (OSError, socket.timeout) as exc:
        raise MailboxScanError(
            "Could not connect to the mailbox server. Check the network and IMAP server settings."
        ) from exc
    finally:
        if mail is not None:
            try:
                mail.logout()
            except imaplib.IMAP4.error:
                pass


def _emit_scan_progress(progress_callback, message, current=None, total=None):
    """Emit detailed progress while keeping older two-argument callbacks working."""
    if not progress_callback:
        return

    try:
        progress_callback(message, current, total)
    except TypeError:
        if current is not None and total is not None:
            progress_callback(current, total)
