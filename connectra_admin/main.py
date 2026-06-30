"""Entry point for the Connectra Admin desktop application."""

import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ui_admin import AdminWindow, AdminAuthDialog
from runtime_setup import initialize_runtime
from database_admin import add_admin_account, get_admin_accounts, verify_admin_login


def main():
    """Run admin authentication and open the Admin dashboard."""

    initialize_runtime()

    app = QApplication(sys.argv)

    existing_admins = get_admin_accounts()

    auth_dialog = AdminAuthDialog(has_existing_admin=bool(existing_admins))

    if not auth_dialog.exec():
        sys.exit(0)

    email, password = auth_dialog.get_credentials()

    if not email or not password:
        QMessageBox.warning(None, "Error", "Email and password are required")
        sys.exit(0)

    if not existing_admins:
        # first-time setup: register this admin
        add_admin_account(email, password)
    elif not verify_admin_login(email, password):
        QMessageBox.warning(None, "Login Failed", "Invalid admin email or password")
        sys.exit(0)

    window = AdminWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
