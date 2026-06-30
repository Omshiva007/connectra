"""Entry point for the Connectra User desktop application."""

import os
import sys

from PySide6.QtWidgets import QApplication

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui_main import DashboardWindow, SetupWindow
from runtime_setup import initialize_runtime
from connectra_core.license_auth import get_installed_identity, get_local_identity, verify_local_login
from connectra_core.local_credentials import load_mailbox_key, load_session, save_session


class ConnectraApp:
    """Coordinates login flow and the main user dashboard window."""

    def __init__(self):
        """Create the Qt application and wire login actions."""
        initialize_runtime()

        self.app = QApplication(sys.argv)

        self.setup_window = SetupWindow()
        self.dashboard_window = None

        self.setup_window.connect_button.clicked.connect(self.handle_login)
        self.try_restore_session()

    def try_restore_session(self):
        """Open the dashboard directly when a persisted session is available."""
        email = load_session()
        if not email:
            return

        identity = get_installed_identity()
        if identity.get("email") != email:
            return

        mailbox_key = load_mailbox_key(email)
        if not mailbox_key:
            return

        self.open_dashboard(email, mailbox_key)

    def handle_login(self):
        """Validate the signed local license before opening the dashboard."""
        email = self.setup_window.email_input.text().strip()

        passcode = self.setup_window.passcode_input.text().strip()

        if not email or not passcode:
            self.setup_window.status_label.setText("Enter email and passcode")
            return

        is_valid, message = verify_local_login(email, passcode)
        if not is_valid:
            self.setup_window.status_label.setText(message)
            return

        has_identity, identity_message, _ = get_local_identity(email, passcode)
        if not has_identity:
            self.setup_window.status_label.setText(identity_message)
            return

        mailbox_key = load_mailbox_key(email)
        if not mailbox_key:
            self.setup_window.status_label.setText("Add and verify your mailbox/API key.")
            self.open_dashboard(email, "")
            return

        save_session(email)
        self.open_dashboard(email, mailbox_key)

    def open_dashboard(self, email, mailbox_key):
        """Show the dashboard for a signed-in user."""
        self.dashboard_window = DashboardWindow(email, mailbox_key)
        self.dashboard_window.logout_requested.connect(self.handle_logout)
        self.dashboard_window.show()
        self.setup_window.hide()

    def handle_logout(self):
        """Return to login after the user explicitly logs out."""
        self.dashboard_window = None
        self.setup_window.show()

    def run(self):
        """Show the login window and start the Qt event loop."""
        if self.dashboard_window is None:
            self.setup_window.show()
        sys.exit(self.app.exec())


if __name__ == "__main__":
    app = ConnectraApp()
    app.run()
