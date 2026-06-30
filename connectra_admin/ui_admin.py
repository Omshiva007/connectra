"""Qt implementation of the Connectra Admin desktop application."""

import base64
import mimetypes

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QTextEdit,
    QDialog,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QInputDialog,
    QCheckBox,
    QTabWidget,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from template_manager import (
    list_templates,
    save_template,
    load_template,
    delete_template,
    publish_templates
)

from holiday_importer import import_holiday_excel
from database_admin import (
    get_holidays,
    get_users,
    add_user,
    update_user,
    delete_user,
    get_user_employee_id,
    get_user_login_passcode,
    get_setting,
    set_setting,
)
from user_app_bundle import create_user_app_bundle, find_existing_user_exe
from activity_viewer import get_logs
from activity_viewer import get_activity_summary
from activity_viewer import export_logs_csv
from connectra_core.template_renderer import render_template_preview
from connectra_core.update_package import create_generic_update_package
from connectra_core.version import APP_VERSION


class TemplateEditor(QDialog):
    """Dialog for creating, editing, and previewing email templates."""

    def __init__(self, name="", subject="", body="", plain_body="", html_body=""):
        """Build the template editor form and live preview panel."""
        super().__init__()

        self.setWindowTitle("Template Editor")
        self.resize(900, 520)

        root = QVBoxLayout()

        header = QLabel("Edit Email Template")
        header.setObjectName("sectionTitle")
        root.addWidget(header)

        main = QHBoxLayout()

        # left: form fields
        form_col = QVBoxLayout()

        form_col.addWidget(QLabel("Template Name"))
        self.name_input = QLineEdit()
        self.name_input.setText(name)
        form_col.addWidget(self.name_input)

        form_col.addWidget(QLabel("Subject"))
        self.subject_input = QLineEdit()
        self.subject_input.setText(subject)
        form_col.addWidget(self.subject_input)

        self.body_tabs = QTabWidget()

        plain_tab = QWidget()
        plain_layout = QVBoxLayout()
        self.plain_body_input = QTextEdit()
        self.plain_body_input.setAcceptRichText(False)
        self.plain_body_input.setPlainText(plain_body or ("" if body.lstrip().startswith("<") else body))
        plain_layout.addWidget(self.plain_body_input)
        plain_tab.setLayout(plain_layout)

        html_tab = QWidget()
        html_layout = QVBoxLayout()
        self.html_body_input = QTextEdit()
        self.html_body_input.setAcceptRichText(False)
        self.html_body_input.setPlainText(html_body or (body if body.lstrip().startswith("<") else ""))
        self.insert_image_btn = QPushButton("Insert Image")
        html_layout.addWidget(self.html_body_input)
        html_layout.addWidget(self.insert_image_btn)
        html_tab.setLayout(html_layout)

        self.body_tabs.addTab(plain_tab, "Plain Text Body")
        self.body_tabs.addTab(html_tab, "HTML Body")
        form_col.addWidget(self.body_tabs)

        main.addLayout(form_col, stretch=2)

        # right: live preview
        preview_col = QVBoxLayout()
        preview_label = QLabel("Preview")
        preview_col.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        preview_col.addWidget(self.preview)

        main.addLayout(preview_col, stretch=2)

        root.addLayout(main)

        # footer buttons
        footer = QHBoxLayout()
        footer.addStretch()
        self.save_btn = QPushButton("Save")
        footer.addWidget(self.save_btn)
        root.addLayout(footer)

        self.setLayout(root)

        self.save_btn.clicked.connect(self.save)
        self.insert_image_btn.clicked.connect(self.insert_image)

        # wiring for live preview
        self.name_input.textChanged.connect(self.update_preview)
        self.subject_input.textChanged.connect(self.update_preview)
        self.plain_body_input.textChanged.connect(self.update_preview)
        self.html_body_input.textChanged.connect(self.update_preview)

        self.update_preview()

    def save(self):
        """Persist the edited template and close the dialog."""

        name = self.name_input.text().strip()
        subject = self.subject_input.text().strip()
        plain_body = self.plain_body_input.toPlainText().strip()
        html_body = self.html_body_input.toPlainText().strip()

        if not name:
            return

        save_template(name, subject, plain_body, html_body)

        self.accept()

    def insert_image(self):
        """Insert a selected image as an inline data URI in the HTML body."""
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Email Image",
            "",
            "Images (*.png *.jpg *.jpeg *.gif);;All Files (*)",
        )

        if not image_path:
            return

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith("image/"):
            QMessageBox.warning(self, "Invalid Image", "Select a PNG, JPG, JPEG, or GIF image.")
            return

        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("ascii")

        image_html = (
            f'<img src="data:{mime_type};base64,{encoded}" '
            'alt="" style="max-width:100%; height:auto;">'
        )
        cursor = self.html_body_input.textCursor()
        cursor.insertText(image_html)
        self.html_body_input.setTextCursor(cursor)
        self.body_tabs.setCurrentIndex(1)
        self.update_preview()

    def update_preview(self):
        """Refresh the rendered HTML preview from current editor values."""

        name = self.name_input.text().strip()
        subject = self.subject_input.text().strip()
        plain_body = self.plain_body_input.toPlainText().strip()
        html_body = self.html_body_input.toPlainText().strip()

        self.preview.setHtml(
            render_template_preview(
                name,
                subject,
                plain_body=plain_body,
                html_body=html_body,
            )
        )


class UserEditor(QDialog):
    """Dialog for creating or editing an admin-configured user."""

    def __init__(self, employee_id="", email="", login_passcode=""):
        """Build the user editor for employee ID, email, and login password."""
        super().__init__()

        self.original_email = email
        self.setWindowTitle("Edit User" if email else "Add User")

        layout = QFormLayout()

        self.employee_id_input = QLineEdit()
        self.employee_id_input.setText(employee_id)
        self.employee_id_input.setPlaceholderText("EMP001")
        layout.addRow("Employee ID", self.employee_id_input)

        self.email_input = QLineEdit()
        self.email_input.setText(email)
        self.email_input.setPlaceholderText("user@company.com")
        layout.addRow("User Email", self.email_input)

        self.login_passcode_input = QLineEdit()
        self.login_passcode_input.setText(login_passcode)
        self.login_passcode_input.setEchoMode(QLineEdit.Password)
        self.login_passcode_input.setPlaceholderText("Passcode the user enters in the User App")
        layout.addRow("User App Login Password", self.login_passcode_input)

        self.show_secrets_checkbox = QCheckBox("Show saved login password")
        layout.addRow("", self.show_secrets_checkbox)

        self.save_btn = QPushButton("Save User")
        layout.addRow("", self.save_btn)

        self.setLayout(layout)
        self.show_secrets_checkbox.stateChanged.connect(self.toggle_secret_visibility)
        self.save_btn.clicked.connect(self.save)

    def toggle_secret_visibility(self):
        """Show or hide saved user secrets in the editor during UAT."""
        echo_mode = (
            QLineEdit.Normal
            if self.show_secrets_checkbox.isChecked()
            else QLineEdit.Password
        )
        self.login_passcode_input.setEchoMode(echo_mode)

    def save(self):
        """Persist the user record through admin database helpers."""

        employee_id = self.employee_id_input.text().strip()
        email = self.email_input.text().strip()
        login_passcode = self.login_passcode_input.text().strip()

        if not employee_id or not email or not login_passcode:
            QMessageBox.warning(
                self,
                "Missing User Details",
                "Employee ID, user email, and User App login password are required.",
            )
            return

        if self.original_email:
            update_user(self.original_email, employee_id, email, login_passcode)
        else:
            add_user(employee_id, email, login_passcode)

        self.accept()


class AdminAuthDialog(QDialog):
    """Login/register dialog shown before opening the Admin dashboard."""

    def __init__(self, has_existing_admin: bool):
        """Build the auth dialog for first-time registration or login."""
        super().__init__()

        self.has_existing_admin = has_existing_admin

        self.setWindowTitle("Connectra Admin")
        self.resize(420, 220)

        layout = QVBoxLayout()

        header = QVBoxLayout()
        title = QLabel("Connectra Admin")
        subtitle = QLabel(
            "Enter admin email and password to manage templates, users, and settings."
        )
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addWidget(subtitle)

        layout.addLayout(header)

        form = QFormLayout()

        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form.addRow("Email", self.email_input)
        form.addRow("Admin Password", self.password_input)

        layout.addLayout(form)

        self.primary_btn = QPushButton(
            "Login" if has_existing_admin else "Register Admin"
        )
        layout.addWidget(self.primary_btn)

        self.setLayout(layout)

        # reuse main dark theme
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0F172A;
                color: #E2E8F0;
                font-family: Segoe UI, system-ui;
                font-size: 10pt;
            }

            QLineEdit {
                background-color: #1E293B;
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
            """
        )

        self.primary_btn.clicked.connect(self.accept)

    def get_credentials(self):
        """Return trimmed admin credentials from the dialog fields."""

        return self.email_input.text().strip(), self.password_input.text().strip()


class AdminWindow(QMainWindow):
    """Main Admin dashboard window for templates, users, reports, and settings."""

    def __init__(self):
        """Build the Admin dashboard shell and load initial data."""
        super().__init__()

        self.setWindowTitle("Connectra Admin")
        self.resize(1200, 750)

        main_layout = QHBoxLayout()

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.addItem("Templates")
        self.sidebar.addItem("Holiday Calendar")
        self.sidebar.addItem("Users")
        self.sidebar.addItem("Activity Dashboard")
        self.sidebar.addItem("Settings")
        self.sidebar.setMaximumWidth(220)

        # Content area
        self.stack = QStackedWidget()

        self.templates_page = self.build_templates_page()
        self.holiday_page = self.build_holiday_page()
        self.users_page = self.build_users_page()
        self.activity_page = self.build_activity_page()
        self.settings_page = self.build_settings_page()

        self.stack.addWidget(self.templates_page)
        self.stack.addWidget(self.holiday_page)
        self.stack.addWidget(self.users_page)
        self.stack.addWidget(self.activity_page)
        self.stack.addWidget(self.settings_page)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        container = QWidget()
        container.setLayout(main_layout)

        self.setCentralWidget(container)

        self.apply_theme()

        self.refresh_templates()
        self.load_holidays()
        self.load_users()
        self.load_activity()
        self.load_settings()

    # Theme
    def apply_theme(self):
        """Apply the shared dark theme used across Admin screens."""

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

        QStackedWidget {
            background-color: #020617;
        }

        QTableWidget {
            background-color: #020617;
            border: 1px solid #1E293B;
        }

        QTextEdit, QLineEdit, QComboBox {
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

        QLabel#sectionTitle {
            font-size: 11pt;
            font-weight: 600;
        }
        """)

    # Templates Page
    def build_templates_page(self):
        """Create the template management page."""

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Templates")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.template_list = QListWidget()
        layout.addWidget(self.template_list)

        btn_layout = QHBoxLayout()

        self.create_btn = QPushButton("Create")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.publish_btn = QPushButton("Publish")

        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.publish_btn)

        layout.addLayout(btn_layout)

        page.setLayout(layout)

        self.create_btn.clicked.connect(self.create_template)
        self.edit_btn.clicked.connect(self.edit_template)
        self.delete_btn.clicked.connect(self.delete_template)
        self.publish_btn.clicked.connect(self.publish_templates)

        return page

    # Holiday Page
    def build_holiday_page(self):
        """Create the holiday calendar import and review page."""

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Holiday Calendar")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.upload_holiday_btn = QPushButton("Upload Holiday Excel")
        layout.addWidget(self.upload_holiday_btn)

        self.holiday_table = QTableWidget()
        self.holiday_table.setColumnCount(6)
        self.holiday_table.setHorizontalHeaderLabels([
            "Holiday", "Date", "Region", "Template", "Reminder Days", "Active"
        ])

        layout.addWidget(self.holiday_table)

        page.setLayout(layout)

        self.upload_holiday_btn.clicked.connect(self.upload_holidays)

        return page

    # Users Page
    def build_users_page(self):
        """Create the user management and installer builder page."""

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Configured Users")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(
            ["Employee ID", "Email", "Login Password", "Active"]
        )

        layout.addWidget(self.users_table)

        btn_layout = QHBoxLayout()

        self.add_user_btn = QPushButton("Add User")
        self.edit_user_btn = QPushButton("Edit Selected User")
        self.delete_user_btn = QPushButton("Delete Selected User")
        self.build_installer_btn = QPushButton("Build Installer for Selected User")
        self.build_update_btn = QPushButton("Build Generic User Update")

        btn_layout.addWidget(self.add_user_btn)
        btn_layout.addWidget(self.edit_user_btn)
        btn_layout.addWidget(self.delete_user_btn)
        btn_layout.addWidget(self.build_installer_btn)
        btn_layout.addWidget(self.build_update_btn)

        layout.addLayout(btn_layout)

        page.setLayout(layout)

        self.add_user_btn.clicked.connect(self.add_user)
        self.edit_user_btn.clicked.connect(self.edit_user)
        self.delete_user_btn.clicked.connect(self.delete_user)
        self.build_installer_btn.clicked.connect(self.build_user_installer)
        self.build_update_btn.clicked.connect(self.build_generic_update)

        return page

    # Activity Page
    def build_activity_page(self):
        """Create the activity reporting page with export controls."""

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("User Activity")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(5)
        self.activity_table.setHorizontalHeaderLabels(
            ["Time", "User", "Client", "Template", "Recipients"]
        )

        self.activity_summary = QLabel("")
        self.activity_summary.setObjectName("sectionTitle")
        layout.addWidget(self.activity_summary)
        layout.addWidget(self.activity_table)

        self.refresh_btn = QPushButton("Refresh")
        self.export_activity_btn = QPushButton("Export CSV")

        activity_buttons = QHBoxLayout()
        activity_buttons.addWidget(self.refresh_btn)
        activity_buttons.addWidget(self.export_activity_btn)
        layout.addLayout(activity_buttons)

        page.setLayout(layout)

        self.refresh_btn.clicked.connect(self.load_activity)
        self.export_activity_btn.clicked.connect(self.export_activity)

        return page

    # Settings Page
    def build_settings_page(self):
        """Create branding, mailbox, and rollout settings controls."""

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        form = QFormLayout()

        self.logo_label = QLabel("No logo selected")
        self.logo_label.setMinimumHeight(80)
        self.logo_label.setStyleSheet("border: 1px dashed #4B5563;")

        self.logo_path_display = QLineEdit()
        self.logo_path_display.setReadOnly(True)

        self.choose_logo_btn = QPushButton("Choose Logo")
        self.save_logo_btn = QPushButton("Save Logo")

        self.imap_server_input = QLineEdit()
        self.smtp_server_input = QLineEdit()
        self.smtp_port_input = QLineEdit()
        self.smtp_tls_checkbox = QCheckBox("Use TLS")
        self.mail_provider_input = QLineEdit()

        self.available_version_input = QLineEdit()
        self.approved_version_input = QLineEdit()
        self.installer_url_input = QLineEdit()
        self.release_notes_input = QTextEdit()
        self.release_notes_input.setMaximumHeight(90)

        form.addRow("Current Logo", self.logo_label)
        form.addRow("Logo Path", self.logo_path_display)
        form.addRow("", self.choose_logo_btn)
        form.addRow("", self.save_logo_btn)
        form.addRow(QLabel("Mailbox Settings"))
        form.addRow("Provider", self.mail_provider_input)
        form.addRow("IMAP Server", self.imap_server_input)
        form.addRow("SMTP Server", self.smtp_server_input)
        form.addRow("SMTP Port", self.smtp_port_input)
        form.addRow("", self.smtp_tls_checkbox)
        form.addRow(QLabel("Version Rollout"))
        form.addRow("Available Version", self.available_version_input)
        form.addRow("Approved Version", self.approved_version_input)
        form.addRow("Installer URL", self.installer_url_input)
        form.addRow("Release Notes", self.release_notes_input)

        self.save_mail_btn = QPushButton("Save Mail Settings")
        self.save_rollout_btn = QPushButton("Save Rollout Settings")
        form.addRow("", self.save_mail_btn)
        form.addRow("", self.save_rollout_btn)

        layout.addLayout(form)
        layout.addStretch()

        page.setLayout(layout)

        self.choose_logo_btn.clicked.connect(self.choose_logo)
        self.save_logo_btn.clicked.connect(self.save_logo)
        self.save_mail_btn.clicked.connect(self.save_mail_settings)
        self.save_rollout_btn.clicked.connect(self.save_rollout_settings)

        return page

    # Template Logic
    def refresh_templates(self):
        """Reload template names into the template list."""

        self.template_list.clear()

        for t in list_templates():
            self.template_list.addItem(t)

    def create_template(self):
        """Open a blank template editor."""

        editor = TemplateEditor()

        if editor.exec():
            self.refresh_templates()

    def edit_template(self):
        """Open the selected template for editing."""

        item = self.template_list.currentItem()

        if not item:
            return

        data = load_template(item.text())

        editor = TemplateEditor(
            data["name"],
            data["subject"],
            data.get("body", ""),
            data.get("plain_body", ""),
            data.get("html_body", ""),
        )

        if editor.exec():
            self.refresh_templates()

    def delete_template(self):
        """Delete the selected admin template."""

        item = self.template_list.currentItem()

        if not item:
            return

        delete_template(item.text())

        self.refresh_templates()

    def publish_templates(self):
        """Publish admin-approved templates to the runtime folder."""

        publish_templates()

        QMessageBox.information(self, "Success", "Templates published")

    # Holiday Logic
    def upload_holidays(self):
        """Import holiday calendar rows from a selected Excel file."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Holiday Excel",
            "",
            "Excel Files (*.xlsx)"
        )

        if file_path:

            import_holiday_excel(file_path)

            QMessageBox.information(self, "Success", "Holiday calendar uploaded")

            self.load_holidays()

    def load_holidays(self):
        """Load holiday rows into the Admin table."""

        holidays = get_holidays()

        self.holiday_table.setRowCount(len(holidays))

        for row, data in enumerate(holidays):

            for col, value in enumerate(data):

                self.holiday_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value))
                )

    # Users Logic
    def load_users(self):
        """Load configured users into the Admin table."""

        users = get_users()

        self.users_table.setRowCount(len(users))

        for row, data in enumerate(users):

            for col, value in enumerate(data):

                self.users_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value))
                )

    def add_user(self):
        """Open the new-user dialog and refresh the table after save."""

        editor = UserEditor()

        if editor.exec():
            self.load_users()

    def edit_user(self):
        """Open the selected user's password editor."""

        row = self.users_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to edit.")
            return

        email_item = self.users_table.item(row, 1)
        if not email_item:
            return

        email = email_item.text()
        employee_id = get_user_employee_id(email) or ""
        current_login_passcode = get_user_login_passcode(email) or ""

        editor = UserEditor(
            employee_id=employee_id,
            email=email,
            login_passcode=current_login_passcode,
        )

        if editor.exec():
            self.load_users()

    def delete_user(self):
        """Delete the selected user after admin confirmation."""

        row = self.users_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to delete.")
            return

        email_item = self.users_table.item(row, 1)
        if not email_item:
            return

        email = email_item.text()
        answer = QMessageBox.question(
            self,
            "Delete User",
            f"Delete {email} and its bootstrap identity?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        deleted_count = delete_user(email)
        if deleted_count:
            QMessageBox.information(self, "Deleted", f"Deleted user:\n{email}")
        else:
            QMessageBox.warning(self, "Not Found", "The selected user was not found.")

        self.load_users()

    def build_user_installer(self):
        """Build a licensed user installer ZIP for the selected user."""

        row = self.users_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to build an installer for.")
            return

        email_item = self.users_table.item(row, 1)
        if not email_item:
            return

        email = email_item.text()
        employee_id = get_user_employee_id(email) or ""
        user_passcode = get_user_login_passcode(email) or ""
        if not employee_id:
            QMessageBox.warning(
                self,
                "Missing Employee ID",
                "Add this user's employee ID before building the bootstrap installer.",
            )
            return

        if not user_passcode:
            QMessageBox.warning(
                self,
                "Missing Login Password",
                "Add this user's User App login password before building the installer.",
            )
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Bootstrap Installer Zip",
            f"connectra_bootstrap_{employee_id}.zip",
            "Zip Files (*.zip)"
        )

        if not output_path:
            return

        try:
            create_user_app_bundle(
                output_path,
                user_email=email,
                user_passcode=user_passcode,
                employee_id=employee_id,
            )
            QMessageBox.information(
                self,
                "Success",
                f"Bootstrap installer saved to:\n{output_path}\n\n"
                f"Share this User App login password securely with the user:\n{user_passcode}\n\n"
                "The user will add their mailbox/API key locally on first login.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))

    def build_generic_update(self):
        """Build one signed generic User update package for eligible employees."""
        users = get_users()
        employee_ids = [row[0] for row in users if row[0]]
        if not employee_ids:
            QMessageBox.warning(
                self,
                "No Employees",
                "Add employee IDs before building a generic update package.",
            )
            return

        update_version, ok = QInputDialog.getText(
            self,
            "Update Version",
            "Enter User app update version:",
            text=APP_VERSION,
        )
        if not ok:
            return

        update_version = update_version.strip()
        if not update_version:
            QMessageBox.warning(self, "Missing Version", "Update version is required.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Generic User Update",
            f"connectra_user_update_{update_version}.connectra-update.zip",
            "Connectra Update (*.zip)"
        )

        if not output_path:
            return

        try:
            user_exe_path = find_existing_user_exe()
            if not user_exe_path:
                raise FileNotFoundError(
                    "Could not find connectra_user.exe for the generic update package. "
                    "Place connectra_user.exe next to connectra_admin.exe, or keep the "
                    "repo dist output available before building the update."
                )

            create_generic_update_package(
                output_path,
                user_exe_path,
                employee_ids,
                update_version,
                "Admin-approved generic User app update.",
            )
            QMessageBox.information(
                self,
                "Success",
                f"Generic update package saved to:\n{output_path}\n\n"
                f"Eligible employees: {len(employee_ids)}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))

    # Activity Logic
    def load_activity(self):
        """Refresh activity rows and dashboard summary counters."""

        logs = get_logs()
        summary = get_activity_summary()
        self.activity_summary.setText(
            "Emails sent: {emails_sent} | Active users: {active_users} | "
            "Client domains: {client_domains} | Recipients: {recipients}".format(
                **summary
            )
        )

        self.activity_table.setRowCount(len(logs))

        for row, data in enumerate(logs):

            for col, value in enumerate(data):

                self.activity_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value))
                )

    def export_activity(self):
        """Export activity rows to a user-selected CSV file."""
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Activity CSV",
            "connectra_activity.csv",
            "CSV Files (*.csv)",
        )

        if not output_path:
            return

        try:
            count = export_logs_csv(output_path)
            QMessageBox.information(self, "Exported", f"Exported {count} activity rows")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    # Settings Logic
    def load_settings(self):
        """Load persisted branding, mailbox, and rollout settings."""

        logo_path = get_setting("logo_path")

        if logo_path:
            self.logo_path_display.setText(logo_path)
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    160,
                    80,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.logo_label.setPixmap(scaled)

        self.mail_provider_input.setText(get_setting("mail_provider") or "gmail")
        self.imap_server_input.setText(get_setting("imap_server") or "imap.gmail.com")
        self.smtp_server_input.setText(get_setting("smtp_server") or "smtp.gmail.com")
        self.smtp_port_input.setText(get_setting("smtp_port") or "587")
        self.smtp_tls_checkbox.setChecked((get_setting("smtp_use_tls") or "1") == "1")

        self.available_version_input.setText(get_setting("available_version") or "")
        self.approved_version_input.setText(get_setting("approved_version") or "")
        self.installer_url_input.setText(get_setting("installer_url") or "")
        self.release_notes_input.setText(get_setting("release_notes") or "")

    def choose_logo(self):
        """Select a logo image path for Admin-managed branding."""

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.svg)",
        )

        if not file_path:
            return

        self.logo_path_display.setText(file_path)

    def save_logo(self):
        """Persist the selected logo path."""

        path = self.logo_path_display.text().strip()

        if not path:
            return

        set_setting("logo_path", path)
        self.load_settings()

    def save_mail_settings(self):
        """Persist mailbox provider and SMTP/IMAP settings."""
        port = self.smtp_port_input.text().strip()
        if not port.isdigit():
            QMessageBox.warning(self, "Invalid Port", "SMTP port must be a number.")
            return

        set_setting("mail_provider", self.mail_provider_input.text().strip() or "gmail")
        set_setting("imap_server", self.imap_server_input.text().strip() or "imap.gmail.com")
        set_setting("smtp_server", self.smtp_server_input.text().strip() or "smtp.gmail.com")
        set_setting("smtp_port", port)
        set_setting("smtp_use_tls", "1" if self.smtp_tls_checkbox.isChecked() else "0")
        QMessageBox.information(self, "Saved", "Mailbox settings saved")

    def save_rollout_settings(self):
        """Persist admin-approved rollout metadata shown to user apps."""
        set_setting("available_version", self.available_version_input.text().strip())
        set_setting("approved_version", self.approved_version_input.text().strip())
        set_setting("installer_url", self.installer_url_input.text().strip())
        set_setting("release_notes", self.release_notes_input.toPlainText().strip())
        QMessageBox.information(self, "Saved", "Rollout settings saved")
