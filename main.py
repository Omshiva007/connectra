import sys
from PySide6.QtWidgets import QApplication, QInputDialog
from ui_main import SetupWindow, DashboardWindow
from database import initialize_database, get_connection, get_config
from email_scanner import scan_mailbox


def save_user(email):
    domain = email.split("@")[1]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO app_config(key,value) VALUES(?,?)",
        ("user_email", email),
    )

    cursor.execute(
        "INSERT OR REPLACE INTO app_config(key,value) VALUES(?,?)",
        ("internal_domain", domain),
    )

    conn.commit()
    conn.close()


def launch_setup():
    window = SetupWindow()

    def handle_save():
        email = window.email_input.text()

        if "@" not in email:
            window.status_label.setText("Invalid email")
            return

        save_user(email)

        window.status_label.setText("Saved. Restart app.")

    window.connect_button.clicked.connect(handle_save)

    return window


def launch_dashboard():
    window = DashboardWindow()

    def handle_scan():

        email = get_config("user_email")
        internal = get_config("internal_domain")

        password, ok = QInputDialog.getText(
            window,
            "Email Password",
            "Enter App Password:"
        )

        if not ok or not password:
            window.status_label.setText("Scan cancelled")
            return

        options = [
            "1 Day",
            "30 Days",
            "90 Days",
            "180 Days",
            "1 Year",
            "All"
        ]

        choice, ok = QInputDialog.getItem(
            window,
            "Scan Range",
            "Select email scan range:",
            options,
            1,
            False
        )

        if not ok:
            window.status_label.setText("Scan cancelled")
            return

        days_map = {
            "1 Day": 1,
            "7 Day": 7,
            "30 Days": 30,
            "90 Days": 90,
            "180 Days": 180,
            "1 Year": 365,
            "All": 36500
        }

        days = days_map[choice]

        def progress(current, total):
            window.status_label.setText(f"Scanning {current} / {total} emails")
            QApplication.processEvents()

        window.status_label.setText("Scanning mailbox...")

        domains = scan_mailbox(email, password, internal, days, progress)

        window.status_label.setText(f"{len(domains)} domains found")

        window.load_domains()

    window.scan_button.clicked.connect(handle_scan)

    window.refresh_button.clicked.connect(window.load_domains)

    window.load_domains()

    return window


def main():
    initialize_database()

    app = QApplication(sys.argv)

    saved = get_config("user_email")

    if saved:
        window = launch_dashboard()
    else:
        window = launch_setup()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()