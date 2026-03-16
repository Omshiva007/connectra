import sys
from PySide6.QtWidgets import QApplication, QMessageBox

from ui_admin import AdminWindow, AdminAuthDialog
from runtime_setup import initialize_runtime
from database_admin import get_users, add_user


def main():

    initialize_runtime()

    app = QApplication(sys.argv)

    existing_users = get_users()

    auth_dialog = AdminAuthDialog(has_existing_admin=bool(existing_users))

    if not auth_dialog.exec():
        sys.exit(0)

    email, password = auth_dialog.get_credentials()

    if not email or not password:
        QMessageBox.warning(None, "Error", "Email and password are required")
        sys.exit(0)

    if not existing_users:
        # first-time setup: register this admin
        add_user(email, password)

    window = AdminWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()