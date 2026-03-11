import sys
from PySide6.QtWidgets import QApplication

from ui_admin import AdminWindow
from runtime_setup import initialize_runtime


def main():

    initialize_runtime()

    app = QApplication(sys.argv)

    window = AdminWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()