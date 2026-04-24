import os
import sys

from PySide6.QtWidgets import QApplication

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui_main import DashboardWindow, SetupWindow
from connectra_core.license_auth import verify_local_login


class ConnectraApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        self.setup_window = SetupWindow()
        self.dashboard_window = None

        self.setup_window.connect_button.clicked.connect(self.handle_login)

    def handle_login(self):
        email = self.setup_window.email_input.text().strip()

        passcode = self.setup_window.passcode_input.text().strip()

        if not email or not passcode:
            self.setup_window.status_label.setText("Enter email and passcode")
            return

        is_valid, message = verify_local_login(email, passcode)
        if not is_valid:
            self.setup_window.status_label.setText(message)
            return

        self.dashboard_window = DashboardWindow(email, passcode)
        self.dashboard_window.show()
        self.setup_window.hide()

    def run(self):
        self.setup_window.show()
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = ConnectraApp()
    app.run()