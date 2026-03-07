from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
)

from database import get_connection


class SetupWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Connectra Setup")

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Email"))

        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("App Password"))

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.connect_button = QPushButton("Save")
        layout.addWidget(self.connect_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)


class DashboardWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Connectra Dashboard")
        self.setMinimumSize(900, 500)

        main_layout = QVBoxLayout()

        title = QLabel("Connectra Client Dashboard")
        main_layout.addWidget(title)

        actions_layout = QHBoxLayout()

        self.scan_button = QPushButton("Scan Emails")
        actions_layout.addWidget(self.scan_button)

        self.refresh_button = QPushButton("Refresh")
        actions_layout.addWidget(self.refresh_button)

        main_layout.addLayout(actions_layout)

        panels_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Client Domains"))

        self.domain_list = QListWidget()
        left_layout.addWidget(self.domain_list)

        panels_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Contacts"))

        self.contact_list = QListWidget()
        right_layout.addWidget(self.contact_list)

        panels_layout.addLayout(right_layout)

        main_layout.addLayout(panels_layout)

        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

        self.domain_list.itemClicked.connect(self.load_contacts)

    def load_domains(self):

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT domain FROM clients ORDER BY domain")

        rows = cursor.fetchall()

        self.domain_list.clear()

        for r in rows:
            self.domain_list.addItem(r[0])

        conn.close()

    def load_contacts(self, item):

        domain = item.text()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT email FROM contacts WHERE domain=? ORDER BY email",
            (domain,)
        )

        rows = cursor.fetchall()

        self.contact_list.clear()

        for r in rows:
            self.contact_list.addItem(r[0])

        conn.close()