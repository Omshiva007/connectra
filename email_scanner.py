import imaplib
import email
import os
from email.utils import getaddresses
from datetime import datetime, timedelta
from database import get_connection, get_config

LOCK_FILE = "scan.lock"


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        raise Exception("Scan already running.")
    with open(LOCK_FILE, "w") as f:
        f.write("locked")


def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def save_last_scan():
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().strftime("%d-%b-%Y")

    cursor.execute(
        "INSERT OR REPLACE INTO app_config(key,value) VALUES(?,?)",
        ("last_scan_date", now),
    )

    conn.commit()
    conn.close()


def get_last_scan():
    value = get_config("last_scan_date")
    return value


def scan_mailbox(email_user, password, internal_domain, days, progress_callback=None):

    try:

        acquire_lock()

        password = str(password).strip()

        print("Connecting to IMAP server...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)

        print("Logging in...")
        mail.login(email_user, password)

        mail.select("inbox", readonly=True)

        last_scan = get_last_scan()

        if last_scan:
            print("Incremental scan since:", last_scan)
            status, messages = mail.search(None, f'(SINCE "{last_scan}")')
        else:
            if days > 3650:
                status, messages = mail.search(None, "ALL")
            else:
                date_limit = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
                status, messages = mail.search(None, f'(SINCE "{date_limit}")')

        email_ids = messages[0].split()
        total = len(email_ids)

        conn = get_connection()
        cursor = conn.cursor()

        domains = set()

        for index, eid in enumerate(email_ids):

            if progress_callback:
                progress_callback(index + 1, total)

            status, msg_data = mail.fetch(
                eid,
                "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE)])"
            )

            if not msg_data or not isinstance(msg_data[0], tuple):
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            addresses = []

            if msg.get("from"):
                addresses.append(msg.get("from"))

            if msg.get("to"):
                addresses.append(msg.get("to"))

            if msg.get("cc"):
                addresses.append(msg.get("cc"))

            parsed = getaddresses(addresses)

            for name, addr in parsed:

                if "@" not in addr:
                    continue

                domain = addr.split("@")[1].lower()

                if domain == internal_domain.lower():
                    continue

                domains.add(domain)

                cursor.execute(
                    "INSERT OR IGNORE INTO contacts(email,domain) VALUES(?,?)",
                    (addr.lower(), domain)
                )

            try:
                mail.store(eid, '-FLAGS', '\\Seen')
            except:
                pass

        for d in domains:
            cursor.execute(
                "INSERT OR IGNORE INTO clients(domain) VALUES(?)",
                (d,),
            )

        conn.commit()
        conn.close()

        save_last_scan()

        mail.logout()

        release_lock()

        return domains

    except Exception as e:

        release_lock()

        print("SCAN ERROR:", e)

        return set()