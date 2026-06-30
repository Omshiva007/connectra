"""Qt implementation of the Connectra User desktop application."""

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
    QInputDialog,
    QFileDialog,
    QDialog,
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap

from connectra_core.admin_database import (
    get_setting as get_admin_setting,
)
from connectra_core.database import get_connection as get_user_connection
from connectra_core.template_loader import load_templates
from connectra_core.template_sync import sync_templates
from connectra_core.email_scanner import scan_mailbox, MailboxScanError
from connectra_core.email_sender import send_email, log_email, EmailSendError
from connectra_core.holiday_checker import check_upcoming_holidays
from connectra_core.update_manager import get_update_info, download_approved_update
from connectra_core.update_package import UpdatePackageError, import_generic_update_package
from connectra_core.template_renderer import render_template_html
from connectra_core.local_credentials import clear_session, save_mailbox_key, save_session
from connectra_core.mailbox_connectivity import (
    MailboxConnectivityError,
    test_mailbox_connectivity,
)


class SetupWindow(QWidget):
    """Login window for licensed user email and passcode."""

    def __init__(self):
        """Build the login form shown before the dashboard."""
        super().__init__()

        self.setWindowTitle("Connectra Login")
        self.resize(400, 200)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Enter your licensed email"))

        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("Enter your User App login password"))
        self.passcode_input = QLineEdit()
        self.passcode_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.passcode_input)

        self.connect_button = QPushButton("Login")
        layout.addWidget(self.connect_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.apply_theme()

    def apply_theme(self):
        """Apply the shared dark theme to the login form."""

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


class DashboardWindow(QMainWindow):
    """Main User dashboard for scanning, grouping, and outreach."""

    logout_requested = Signal()

    def __init__(self, email, mailbox_password):
        """Build the dashboard and load existing local state."""

        super().__init__()

        self.user_email = email
        self.mailbox_password = mailbox_password

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
        self.download_update_button = QPushButton("Download Update")
        self.logout_button = QPushButton("Logout")
        self.settings_button = QPushButton("Settings")
        self.download_update_button.setVisible(False)

        template_bar.addSpacing(12)
        template_bar.addWidget(self.refresh_button)
        template_bar.addWidget(self.preview_button)
        template_bar.addWidget(self.send_button)
        template_bar.addWidget(self.download_update_button)
        template_bar.addWidget(self.logout_button)
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
        self.download_update_button.clicked.connect(self.download_update_action)
        self.logout_button.clicked.connect(self.logout)
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_contacts)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setToolTip("Manage mailbox key and admin update packages")

        self.load_domains()
        self.show_holiday_reminder()
        self.show_update_notice()
        self.load_branding()
        self.apply_theme()
        if not self.mailbox_password:
            self.configure_mailbox_key(required=True)

    # --------------------------
    # Scan Progress
    # --------------------------

    def update_scan_progress(self, message, current=None, total=None):
        """Update the scan progress label while IMAP headers are processed."""

        if current is not None and total is not None and total:
            self.scan_status.setText(f"{message} ({current}/{total})")
        else:
            self.scan_status.setText(message)
        QApplication.processEvents()

    def load_branding(self):
        """Load admin-managed branding into the dashboard header."""

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
        """Apply the shared dark theme to the dashboard."""

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
        """Ask consent, scan mailbox headers, and refresh domain groups."""
        if not self.ensure_mailbox_key():
            return

        consent = QMessageBox.question(
            self,
            "Mailbox Scan Consent",
            "Connectra will scan email headers only: To and CC recipients. "
            "Email bodies will not be read. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if consent != QMessageBox.StandardButton.Yes:
            return

        self.scan_button.setEnabled(False)
        self.scan_status.setText("Preparing scan...")
        QApplication.processEvents()

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

        try:
            summary = scan_mailbox(
                self.user_email,
                self.mailbox_password,
                internal,
                days,
                self.update_scan_progress
            )
        except MailboxScanError as exc:
            self.scan_status.setText("Scan failed")
            QMessageBox.warning(self, "Scan Failed", str(exc))
            return
        except Exception as exc:
            self.scan_status.setText("Scan failed")
            QMessageBox.warning(
                self,
                "Scan Failed",
                f"Unexpected scan error: {exc}",
            )
            return
        finally:
            self.scan_button.setEnabled(True)

        messages_scanned = summary.get("messages_scanned", 0)
        contacts_found = summary.get("contacts_found", 0)
        domains_found = summary.get("domains_found", 0)
        result_message = (
            f"Scan completed: {messages_scanned} messages, "
            f"{contacts_found} contacts, {domains_found} domains"
        )

        self.scan_status.setText(result_message)

        QMessageBox.information(self, "Scan", result_message)

        self.load_domains()

    # --------------------------
    # Holiday reminder
    # --------------------------

    def show_holiday_reminder(self):
        """Show upcoming admin-configured holiday reminders."""

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

    def show_update_notice(self):
        """Show an admin-approved update notice and enable download when possible."""
        update_info = get_update_info()

        if not update_info.is_update_available:
            return

        self.download_update_button.setVisible(bool(update_info.installer_url))

        message = f"Version {update_info.approved_version} is approved by admin."
        if update_info.installer_url:
            message = f"{message}\nInstaller: {update_info.installer_url}"
        if update_info.release_notes:
            message = f"{message}\n{update_info.release_notes}"

        current = self.holiday_card.text()
        if current:
            message = f"{current}\n\n{message}"

        self.holiday_card.setText(message)

    def download_update_action(self):
        """Download the admin-approved installer to the local updates folder."""
        try:
            output_path = download_approved_update()
        except Exception as exc:
            QMessageBox.warning(self, "Update Download Failed", str(exc))
            return

        QMessageBox.information(
            self,
            "Update Downloaded",
            f"Update installer downloaded to:\n{output_path}",
        )

    def import_update_action(self, parent=None):
        """Import and validate an admin-generated generic update package."""
        owner = parent or self
        package_path, _ = QFileDialog.getOpenFileName(
            owner,
            "Import Connectra Update",
            "",
            "Connectra Update (*.connectra-update.zip *.zip);;Zip Files (*.zip);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )

        if not package_path:
            return

        try:
            stored_path = import_generic_update_package(package_path)
        except (UpdatePackageError, OSError, ValueError) as exc:
            QMessageBox.warning(owner, "Update Rejected", str(exc))
            return

        QMessageBox.information(
            owner,
            "Update Accepted",
            f"Update package accepted and stored at:\n{stored_path}\n\n"
            "Close Connectra and install the update package to complete the update.",
        )

    # --------------------------
    # Domains
    # --------------------------

    def load_domains(self):
        """Load grouped external domains and contact counts from local SQLite."""

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
        """Filter the domain list by the user's search text."""

        text = self.search_box.text().lower()

        self.domain_list.clear()

        for domain, display in self.all_domains:

            if text in domain.lower():
                self.domain_list.addItem(display)

    # --------------------------
    # Contacts
    # --------------------------

    def load_contacts(self, domain_text):
        """Load selectable contacts for the currently selected domain."""

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
        """Check or uncheck every contact in the selected domain."""

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
        """Refresh user-visible templates from runtime storage."""

        sync_templates()

        self.template_dropdown.clear()

        self.templates = load_templates()

        for t in self.templates:
            self.template_dropdown.addItem(t["name"])

    # --------------------------
    # Send Email
    # --------------------------

    def preview_email(self):
        """Render the selected template and recipients before sending."""
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
            f"{render_template_html(template.get('plain_body', ''), template.get('html_body', ''), template.get('body', ''))}"
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
        """Send the selected template to checked contacts and log activity."""
        if not self.ensure_mailbox_key():
            return

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

        try:
            send_email(
                self.user_email,
                self.mailbox_password,
                recipients,
                template["subject"],
                template.get("body", ""),
                plain_body=template.get("plain_body", ""),
                html_body=template.get("html_body", ""),
            )
        except EmailSendError as exc:
            QMessageBox.warning(self, "Send Failed", str(exc))
            return

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
        """Open user-managed settings for mailbox key and update imports."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(360, 160)

        layout = QVBoxLayout()

        mailbox_status = "Configured" if self.mailbox_password else "Not configured"
        layout.addWidget(QLabel(f"Mailbox/API Key: {mailbox_status}"))

        mailbox_key_btn = QPushButton("Update Mailbox/API Key")
        import_update_btn = QPushButton("Import Admin Update Package")
        close_btn = QPushButton("Close")

        layout.addWidget(mailbox_key_btn)
        layout.addWidget(import_update_btn)
        layout.addStretch()
        layout.addWidget(close_btn)

        dialog.setLayout(layout)

        mailbox_key_btn.clicked.connect(lambda: self.configure_mailbox_key(required=False))
        import_update_btn.clicked.connect(lambda: self.import_update_action(dialog))
        close_btn.clicked.connect(dialog.accept)

        dialog.exec()

    def ensure_mailbox_key(self):
        """Ensure a verified mailbox key exists before scan or send."""
        if self.mailbox_password:
            return True

        QMessageBox.information(
            self,
            "Mailbox Key Required",
            "Add and verify your mailbox/API key before scanning or sending.",
        )
        self.configure_mailbox_key(required=True)
        return bool(self.mailbox_password)

    def configure_mailbox_key(self, required=False):
        """Prompt the user to enter and verify their mailbox/API key."""
        while True:
            key, ok = QInputDialog.getText(
                self,
                "Mailbox/API Key",
                "Enter your mailbox/API app key:",
                QLineEdit.Password,
            )

            if not ok:
                if required and not self.mailbox_password:
                    QMessageBox.warning(
                        self,
                        "Mailbox Key Required",
                        "You must add a working mailbox/API key before using Connectra.",
                    )
                return

            key = key.strip()
            if not key:
                QMessageBox.warning(self, "Missing Key", "Mailbox/API key is required.")
                continue

            try:
                test_mailbox_connectivity(self.user_email, key)
            except MailboxConnectivityError as exc:
                QMessageBox.warning(self, "Mailbox Key Test Failed", str(exc))
                continue

            save_mailbox_key(self.user_email, key)
            save_session(self.user_email)
            self.mailbox_password = key
            QMessageBox.information(self, "Mailbox Key Saved", "Mailbox connectivity test passed.")
            return

    def logout(self):
        """Clear the local session and return to the login screen."""
        clear_session()
        self.close()
        self.logout_requested.emit()
