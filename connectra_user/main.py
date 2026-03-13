import sys
from PySide6.QtWidgets import QApplication

from ui_main import SetupWindow, DashboardWindow
from connectra_core.database import get_connection

def email_allowed(email):
conn = get_connection()
cursor = conn.cursor()

```
cursor.execute(
    "SELECT email FROM users WHERE email=? AND active=1",
    (email,)
)

row = cursor.fetchone()
conn.close()

return row is not None
```

class ConnectraApp:

```
def __init__(self):

    self.app = QApplication(sys.argv)

    self.setup_window = SetupWindow()
    self.dashboard_window = None

    self.setup_window.connect_button.clicked.connect(self.handle_login)

def handle_login(self):

    email = self.setup_window.email_input.text().strip()

    if not email:
        self.setup_window.status_label.setText("Enter email")
        return

    if not email_allowed(email):
        self.setup_window.status_label.setText("Email not authorized")
        return

    self.dashboard_window = DashboardWindow(email)
    self.dashboard_window.show()

    self.setup_window.hide()

def run(self):

    self.setup_window.show()
    sys.exit(self.app.exec())
```

if **name** == "**main**":

```
app = ConnectraApp()
app.run()