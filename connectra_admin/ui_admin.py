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
    get_user_password,
    get_setting,
    set_setting,
)
from user_app_bundle import create_user_app_bundle
from activity_viewer import get_logs


class TemplateEditor(QDialog):

    def __init__(self, name="", subject="", body=""):
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

        form_col.addWidget(QLabel("Body (HTML)"))
        self.body_input = QTextEdit()
        self.body_input.setText(body)
        form_col.addWidget(self.body_input)

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

        # wiring for live preview
        self.name_input.textChanged.connect(self.update_preview)
        self.subject_input.textChanged.connect(self.update_preview)
        self.body_input.textChanged.connect(self.update_preview)

        self.update_preview()

    def save(self):

        name = self.name_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_input.toPlainText().strip()

        if not name:
            return

        save_template(name, subject, body)

        self.accept()

    def update_preview(self):

        name = self.name_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_input.toPlainText().strip()

        header_html = (
            f"<h3>{name or '(untitled)'}</h3>"
            f"<p><b>Subject:</b> {subject}</p>"
            "<hr/>"
        )

        # render body as HTML so tags are applied
        full_html = header_html + body

        self.preview.setHtml(full_html)


class UserEditor(QDialog):

    def __init__(self, email="", password="", lock_email=False):
        super().__init__()

        self.lock_email = lock_email
        self.setWindowTitle("Edit User" if email else "Add User")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("User Email"))

        self.email_input = QLineEdit()
        self.email_input.setText(email)
        if lock_email:
            self.email_input.setReadOnly(True)
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("App Password"))

        self.password_input = QLineEdit()
        self.password_input.setText(password)
        layout.addWidget(self.password_input)

        self.save_btn = QPushButton("Save User")
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        self.save_btn.clicked.connect(self.save)

    def save(self):

        email = self.email_input.text().strip()
        password = self.password_input.text().strip()

        if not email or not password:
            return

        if self.lock_email:
            update_user(email, password)
        else:
            add_user(email, password)

        self.accept()


class AdminAuthDialog(QDialog):

    def __init__(self, has_existing_admin: bool):
        super().__init__()

        self.has_existing_admin = has_existing_admin

        self.setWindowTitle("Connectra Admin")
        self.resize(420, 220)

        layout = QVBoxLayout()

        header = QVBoxLayout()
        title = QLabel("Connectra Admin")
        subtitle = QLabel(
            "Enter admin email and app password to manage templates and settings."
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
        form.addRow("Password", self.password_input)

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

        return self.email_input.text().strip(), self.password_input.text().strip()


class AdminWindow(QMainWindow):

    def __init__(self):
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

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Configured Users")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(2)
        self.users_table.setHorizontalHeaderLabels(["Email", "Active"])

        layout.addWidget(self.users_table)

        btn_layout = QHBoxLayout()

        self.add_user_btn = QPushButton("Add User")
        self.edit_user_btn = QPushButton("Edit Selected User")
        self.build_installer_btn = QPushButton("Build Installer for Selected User")

        btn_layout.addWidget(self.add_user_btn)
        btn_layout.addWidget(self.edit_user_btn)
        btn_layout.addWidget(self.build_installer_btn)

        layout.addLayout(btn_layout)

        page.setLayout(layout)

        self.add_user_btn.clicked.connect(self.add_user)
        self.edit_user_btn.clicked.connect(self.edit_user)
        self.build_installer_btn.clicked.connect(self.build_user_installer)

        return page

    # Activity Page
    def build_activity_page(self):

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

        layout.addWidget(self.activity_table)

        self.refresh_btn = QPushButton("Refresh")
        layout.addWidget(self.refresh_btn)

        page.setLayout(layout)

        self.refresh_btn.clicked.connect(self.load_activity)

        return page

    # Settings Page
    def build_settings_page(self):

        page = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Brand Settings")
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

        form.addRow("Current Logo", self.logo_label)
        form.addRow("Logo Path", self.logo_path_display)
        form.addRow("", self.choose_logo_btn)
        form.addRow("", self.save_logo_btn)

        layout.addLayout(form)
        layout.addStretch()

        page.setLayout(layout)

        self.choose_logo_btn.clicked.connect(self.choose_logo)
        self.save_logo_btn.clicked.connect(self.save_logo)

        return page

    # Template Logic
    def refresh_templates(self):

        self.template_list.clear()

        for t in list_templates():
            self.template_list.addItem(t)

    def create_template(self):

        editor = TemplateEditor()

        if editor.exec():
            self.refresh_templates()

    def edit_template(self):

        item = self.template_list.currentItem()

        if not item:
            return

        data = load_template(item.text())

        editor = TemplateEditor(
            data["name"],
            data["subject"],
            data["body"]
        )

        if editor.exec():
            self.refresh_templates()

    def delete_template(self):

        item = self.template_list.currentItem()

        if not item:
            return

        delete_template(item.text())

        self.refresh_templates()

    def publish_templates(self):

        publish_templates()

        QMessageBox.information(self, "Success", "Templates published")

    # Holiday Logic
    def upload_holidays(self):

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

        editor = UserEditor()

        if editor.exec():
            self.load_users()

    def edit_user(self):

        row = self.users_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to edit.")
            return

        email_item = self.users_table.item(row, 0)
        if not email_item:
            return

        email = email_item.text()
        current_password = get_user_password(email) or ""

        editor = UserEditor(email=email, password=current_password, lock_email=True)

        if editor.exec():
            self.load_users()

    def build_user_installer(self):

        row = self.users_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to build an installer for.")
            return

        email_item = self.users_table.item(row, 0)
        if not email_item:
            return

        email = email_item.text()
        password = get_user_password(email)

        if not password:
            QMessageBox.warning(
                self,
                "Missing Password",
                f"No app password found for {email}. Please edit the user first."
            )
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Installer Zip",
            f"connectra_user_{email.split('@')[0]}.zip",
            "Zip Files (*.zip)"
        )

        if not output_path:
            return

        try:
            create_user_app_bundle(output_path, user_email=email, user_app_password=password)
            QMessageBox.information(self, "Success", f"Installer saved to:\n{output_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))

    # Activity Logic
    def load_activity(self):

        logs = get_logs()

        self.activity_table.setRowCount(len(logs))

        for row, data in enumerate(logs):

            for col, value in enumerate(data):

                self.activity_table.setItem(
                    row,
                    col,
                    QTableWidgetItem(str(value))
                )

    # Settings Logic
    def load_settings(self):

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

    def choose_logo(self):

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

        path = self.logo_path_display.text().strip()

        if not path:
            return

        set_setting("logo_path", path)
        self.load_settings()