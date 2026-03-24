from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QMessageBox,
    QCheckBox,
    QDialog,
    QFormLayout,
)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFormLayout
from PySide6.QtGui import QPixmap

from connectra_core.admin_database import (
    get_connection as get_admin_connection,
    get_setting as get_admin_setting,
)
from connectra_core.database import get_connection as get_user_connection
from connectra_core.template_loader import load_templates
from connectra_core.template_sync import sync_templates
from connectra_core.email_scanner import scan_mailbox
from connectra_core.email_sender import send_email, log_email
from connectra_core.holiday_checker import check_upcoming_holidays
from connectra_core.security import decrypt_password, encrypt_password


def _save_user_password(email: str, new_password: str) -> None:
    """Persist an updated app password for *email* in the admin DB."""
    import logging
    conn = get_admin_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET app_password=? WHERE email=?",
        (encrypt_password(new_password), email),
    )
    if cursor.rowcount == 0:
        logging.warning("_save_user_password: no user found for email %s", email)
    conn.commit()
    conn.close()



def get_password(email):
    conn = get_admin_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT app_password FROM users WHERE email=?",
        (email,),
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        try:
            return decrypt_password(row[0])
        except ValueError:
            # Fallback for passwords stored before encryption was introduced.
            return row[0]

    return None


class SetupWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Connectra Login")
        self.resize(400, 200)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Enter your email"))

        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        self.connect_button = QPushButton("Login")
        layout.addWidget(self.connect_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.apply_theme()

    def apply_theme(self):

        self.setStyleSheet("""
        QWidget {
            background-color: #0F172A;
            color: #E2E8F0;
            font-family: Segoe UI, system-ui;
            font-size: 10pt;
        }

        QPushButton {
            background-color: #6366F1;
            padding: 4px 10px;
            border-radius: 4px;
            min-height: 26px;
        }

        QPushButton:hover {
            background-color: #4F46E5;
        }

        QLineEdit {
            background-color: #1E293B;
            border-radius: 4px;
            padding: 6px;
        }
        """)


class SettingsDialog(QDialog):
    """Allow the user to update their app password from the dashboard."""

    def __init__(self, email: str, parent=None):
        super().__init__(parent)

        self.email = email
        self.new_password: str | None = None

        self.setWindowTitle("Settings")
        self.resize(360, 160)

        layout = QVBoxLayout()

        form = QFormLayout()

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter new app password")

        form.addRow("Email", QLabel(email))
        form.addRow("New App Password", self.password_input)

        layout.addLayout(form)

        self.save_btn = QPushButton("Save")
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        self.save_btn.clicked.connect(self._save)

    def _save(self):
        password = self.password_input.text().strip()
        if not password:
            QMessageBox.warning(self, "Validation", "Password cannot be empty.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Validation", "Password must be at least 8 characters.")
            return
        self.new_password = password
        self.accept()


class DashboardWindow(QMainWindow):

    def __init__(self, email):

        super().__init__()

        self.user_email = email
        self.password = get_password(email)

        self.setWindowTitle("Connectra")
        self.resize(1000, 650)

        container = QWidget()
        main_layout = QVBoxLayout()

        # Header with logo and title
        header = QHBoxLayout()

        self.logo_label = QLabel()
        self.logo_label.setFixedHeight(64)

        title_block = QVBoxLayout()
        title = QLabel("Connectra")
        subtitle = QLabel("Client Greeting Dashboard")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        header.addWidget(self.logo_label)
        header.addLayout(title_block)
        header.addStretch()

        main_layout.addLayout(header)

        # Holiday reminder
        self.holiday_card = QLabel("")
        self.holiday_card.setObjectName("holidayCard")
        main_layout.addWidget(self.holiday_card)

        # Scan + search toolbar
        toolbar_layout = QHBoxLayout()

        # scan range
        self.range_select = QComboBox()
        self.range_select.addItems(
            [
                "1 Day",
                "30 Days",
                "90 Days",
                "180 Days",
                "1 Year",
                "All",
            ]
        )

        range_block = QHBoxLayout()
        range_block.addWidget(QLabel("Scan Range"))
        range_block.addWidget(self.range_select)

        # search
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by domain name...")

        # run scan on the right
        self.scan_button = QPushButton("Run Scan")
        self.scan_status = QLabel("")

        toolbar_layout.addLayout(range_block)
        toolbar_layout.addSpacing(16)
        toolbar_layout.addWidget(self.search_box, stretch=1)
        toolbar_layout.addSpacing(16)
        toolbar_layout.addWidget(self.scan_button)
        toolbar_layout.addWidget(self.scan_status)

        main_layout.addLayout(toolbar_layout)

        # Domain and contacts
        list_layout = QHBoxLayout()

        self.domain_list = QListWidget()

        contact_panel = QVBoxLayout()

        self.select_all_checkbox = QCheckBox("Select All Contacts")
        contact_panel.addWidget(self.select_all_checkbox)

        self.contact_list = QListWidget()
        contact_panel.addWidget(self.contact_list)

        list_layout.addWidget(self.domain_list)
        list_layout.addLayout(contact_panel)

        main_layout.addLayout(list_layout)

        # Templates footer bar
        template_bar = QHBoxLayout()

        template_bar.addWidget(QLabel("Email Template"))

        self.template_dropdown = QComboBox()

        self.templates = load_templates()

        for t in self.templates:
            self.template_dropdown.addItem(t["name"])

        template_bar.addWidget(self.template_dropdown, stretch=1)

        self.refresh_button = QPushButton("Refresh")
        self.preview_button = QPushButton("Preview")
        self.send_button = QPushButton("Send")
        self.settings_button = QPushButton("Settings")

        template_bar.addSpacing(12)
        template_bar.addWidget(self.refresh_button)
        template_bar.addWidget(self.preview_button)
        template_bar.addWidget(self.send_button)
        template_bar.addWidget(self.settings_button)

        main_layout.addLayout(template_bar)

        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # events
        self.scan_button.clicked.connect(self.run_scan)
        self.refresh_button.clicked.connect(self.refresh_templates)
        self.preview_button.clicked.connect(self.preview_email)
        self.domain_list.currentTextChanged.connect(self.load_contacts)
        self.search_box.textChanged.connect(self.filter_domains)
        self.send_button.clicked.connect(self.send_email_action)
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_contacts)
        self.settings_button.clicked.connect(self.open_settings)

        self.load_domains()
        self.show_holiday_reminder()
        self.load_branding()
        self.apply_theme()

    # --------------------------
    # Scan Progress
    # --------------------------

    def update_scan_progress(self, current, total):

        self.scan_status.setText(f"Scanning {current}/{total}")
        QApplication.processEvents()

    def load_branding(self):

        logo_path = get_admin_setting("logo_path")

        if logo_path:
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    160,
                    64,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.logo_label.setPixmap(scaled)

    def apply_theme(self):

        self.setStyleSheet("""
        QWidget {
            background-color: #0F172A;
            color: #E2E8F0;
            font-family: Segoe UI, system-ui;
            font-size: 10pt;
        }

        QListWidget {
            background-color: #020617;
            border: 1px solid #1E293B;
        }

        QLineEdit, QComboBox, QTextEdit {
            background-color: #020617;
            border-radius: 4px;
            padding: 6px;
        }

        QPushButton {
            background-color: #6366F1;
            padding: 4px 10px;
            border-radius: 4px;
            min-height: 26px;
        }

        QPushButton:hover {
            background-color: #4F46E5;
        }

        QLabel#holidayCard {
            background-color: #1E293B;
            padding: 10px;
            border-radius: 8px;
        }
        """)

    def run_scan(self):

        option = self.range_select.currentText()

        days = None

        if option == "1 Day":
            days = 1
        elif option == "30 Days":
            days = 30
        elif option == "90 Days":
            days = 90
        elif option == "180 Days":
            days = 180
        elif option == "1 Year":
            days = 365

        internal = self.user_email.split("@")[1]

        scan_mailbox(
            self.user_email,
            self.password,
            internal,
            days,
            self.update_scan_progress
        )

        self.scan_status.setText("Scan completed")

        QMessageBox.information(self, "Scan", "Scan completed")

        self.load_domains()

    # --------------------------
    # Holiday reminder
    # --------------------------

    def show_holiday_reminder(self):

        holidays = check_upcoming_holidays()

        if not holidays:
            self.holiday_card.setText("No upcoming holiday reminders.")
            return

        messages = []

        for h in holidays:
            messages.append(
                f"{h['holiday']} coming soon. Template: {h['template']}"
            )

        self.holiday_card.setText("\n".join(messages))

    # --------------------------
    # Domains
    # --------------------------

    def load_domains(self):

        self.domain_list.clear()

        conn = get_user_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT domain, COUNT(*) as contact_count
        FROM contacts
        GROUP BY domain
        ORDER BY contact_count DESC
        """)

        rows = cursor.fetchall()

        self.all_domains = []

        for domain, count in rows:

            display = f"{domain} ({count})"

            self.domain_list.addItem(display)

            self.all_domains.append((domain, display))

        conn.close()

    def filter_domains(self):

        text = self.search_box.text().lower()

        self.domain_list.clear()

        for domain, display in self.all_domains:

            if text in domain.lower():
                self.domain_list.addItem(display)

    # --------------------------
    # Contacts
    # --------------------------

    def load_contacts(self, domain_text):

        domain = domain_text.split(" ")[0]

        self.contact_list.clear()

        conn = get_user_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT email FROM contacts WHERE domain=?",
            (domain,)
        )

        rows = cursor.fetchall()

        for r in rows:

            item = QListWidgetItem(r[0])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)

            self.contact_list.addItem(item)

        conn.close()

    def toggle_all_contacts(self):

        checked = self.select_all_checkbox.isChecked()

        for i in range(self.contact_list.count()):

            item = self.contact_list.item(i)

            if checked:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

    # --------------------------
    # Templates
    # --------------------------

    def refresh_templates(self):

        sync_templates()

        self.template_dropdown.clear()

        self.templates = load_templates()

        for t in self.templates:
            self.template_dropdown.addItem(t["name"])

    # --------------------------
    # Send Email
    # --------------------------

    def preview_email(self):
        if not self.domain_list.currentItem():
            return

        recipients = []

        for i in range(self.contact_list.count()):
            item = self.contact_list.item(i)
            if item.checkState() == Qt.Checked:
                recipients.append(item.text())

        if not recipients:
            return

        template_index = self.template_dropdown.currentIndex()
        template = self.templates[template_index]

        # Render HTML body inside a simple wrapper so user sees formatted content
        html = (
            f"<p><b>To:</b> {', '.join(recipients)}</p>"
            f"<p><b>Subject:</b> {template['subject']}</p>"
            "<hr/>"
            f"{template['body']}"
        )

        preview_dialog = QMessageBox(self)
        preview_dialog.setWindowTitle("Preview Email")
        preview_dialog.setTextFormat(Qt.RichText)
        preview_dialog.setText(html)
        preview_dialog.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        answer = preview_dialog.exec()

        if answer != QMessageBox.StandardButton.Ok:
            return

    def send_email_action(self):
        if not self.domain_list.currentItem():
            return

        domain = self.domain_list.currentItem().text().split(" ")[0]

        recipients = []

        for i in range(self.contact_list.count()):

            item = self.contact_list.item(i)

            if item.checkState() == Qt.Checked:
                recipients.append(item.text())

        if not recipients:
            return

        template_index = self.template_dropdown.currentIndex()
        template = self.templates[template_index]

        send_email(
            self.user_email,
            self.password,
            recipients,
            template["subject"],
            template["body"]
        )

        log_email(
            self.user_email,
            domain,
            template["name"],
            len(recipients)
        )

        QMessageBox.information(self, "Success", "Email sent")

    # --------------------------
    # Settings
    # --------------------------

    def open_settings(self):

        dialog = SettingsDialog(self.user_email, parent=self)

        if dialog.exec() and dialog.new_password:
            _save_user_password(self.user_email, dialog.new_password)
            self.password = dialog.new_password
            QMessageBox.information(self, "Settings", "Password updated successfully.")