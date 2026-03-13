import imaplib
import email

from database import get_connection
from filters import is_internal_email


def scan_mailbox(email_user, password, internal_domain, days, progress_callback=None):

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_user, password)

    mail.select("inbox")

    if days:
     import datetime
     since_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
     status, data = mail.search(None, f'(SINCE "{since_date}")')
    else:
     status, data = mail.search(None, "ALL")

    mail_ids = data[0].split()

    total = len(mail_ids)

    conn = get_connection()
    cursor = conn.cursor()

    for index, num in enumerate(mail_ids):

        status, msg_data = mail.fetch(num, "(BODY.PEEK[HEADER])")

        msg = email.message_from_bytes(msg_data[0][1])

        fields = ["from", "to", "cc"]

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
            progress_callback(index + 1, total)

    conn.commit()
    conn.close()

    mail.logout()