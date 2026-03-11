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
)

from template_manager import (
    list_templates,
    save_template,
    load_template,
    delete_template,
    publish_templates
)

from holiday_importer import import_holiday_excel
from database_admin import get_holidays, get_users, add_user
from activity_viewer import get_logs


class TemplateEditor(QDialog):

    def __init__(self, name="", subject="", body=""):
        super().__init__()

        self.setWindowTitle("Template Editor")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Template Name"))
        self.name_input = QTextEdit()
        self.name_input.setText(name)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Subject"))
        self.subject_input = QTextEdit()
        self.subject_input.setText(subject)
        layout.addWidget(self.subject_input)

        layout.addWidget(QLabel("Body"))
        self.body_input = QTextEdit()
        self.body_input.setText(body)
        layout.addWidget(self.body_input)

        self.save_btn = QPushButton("Save")
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

        self.save_btn.clicked.connect(self.save)

    def save(self):

        name = self.name_input.toPlainText().strip()
        subject = self.subject_input.toPlainText().strip()
        body = self.body_input.toPlainText().strip()

        if not name:
            return

        save_template(name, subject, body)

        self.accept()


class UserEditor(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Add User")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("User Email"))

        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("App Password"))

        self.password_input = QLineEdit()
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

        add_user(email, password)

        self.accept()


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
        self.sidebar.setMaximumWidth(220)

        # Content area
        self.stack = QStackedWidget()

        self.templates_page = self.build_templates_page()
        self.holiday_page = self.build_holiday_page()
        self.users_page = self.build_users_page()
        self.activity_page = self.build_activity_page()

        self.stack.addWidget(self.templates_page)
        self.stack.addWidget(self.holiday_page)
        self.stack.addWidget(self.users_page)
        self.stack.addWidget(self.activity_page)

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

    # Theme
    def apply_theme(self):

        self.setStyleSheet("""
        QWidget {
            background-color: #0F172A;
            color: #E2E8F0;
        }

        QListWidget {
            background-color: #1E293B;
            border: none;
        }

        QPushButton {
            background-color: #6366F1;
            padding: 8px;
            border-radius: 6px;
        }

        QPushButton:hover {
            background-color: #4F46E5;
        }

        QTableWidget {
            background-color: #1E293B;
        }

        QTextEdit {
            background-color: #1E293B;
        }
        """)

    # Templates Page
    def build_templates_page(self):

        page = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Templates"))

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

        layout.addWidget(QLabel("Holiday Calendar"))

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

        layout.addWidget(QLabel("Configured Users"))

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(2)
        self.users_table.setHorizontalHeaderLabels(["Email", "Active"])

        layout.addWidget(self.users_table)

        self.add_user_btn = QPushButton("Add User")
        layout.addWidget(self.add_user_btn)

        page.setLayout(layout)

        self.add_user_btn.clicked.connect(self.add_user)

        return page

    # Activity Page
    def build_activity_page(self):

        page = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("User Activity"))

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