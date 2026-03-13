import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from database import get_connection


def log_email(user_email, domain, template_name, recipient_count):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO email_logs(timestamp,user_email,client_domain,template_name,recipient_count)
        VALUES(?,?,?,?,?)
    """, (
        datetime.now().isoformat(),
        user_email,
        domain,
        template_name,
        recipient_count
    ))

    conn.commit()
    conn.close()


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