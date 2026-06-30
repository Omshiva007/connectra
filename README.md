# Connectra

Connectra is a Windows desktop application for managing holiday and client greeting outreach. It has two PySide6 apps:

- **Connectra Admin**: manage templates, holiday calendars, users, mailbox settings, activity reports, and update packages.
- **Connectra User**: scan mailbox headers, group external contacts by client domain, preview templates, send greetings, and import admin-approved updates.

## Current UAT Build

Fresh Windows executables are available in:

- `connectra_admin/dist/connectra_admin.exe`
- `connectra_user/dist/connectra_user.exe`

New builds no longer ship with sample templates. Admin starts with an empty template list; templates are added and published by the admin when needed.

## Key Product Flow

1. Admin creates users with Employee ID, email, and User App login password.
2. Admin builds a one-time bootstrap installer for a selected user.
3. User logs in with licensed email and login password.
4. User adds their own mailbox/API key locally and verifies connectivity.
5. Admin creates and publishes templates.
6. User clicks **Refresh** to pull updated templates.
7. User scans mailbox headers, previews the selected template, and sends emails.
8. Admin can build a generic update package that eligible users import from User app settings.

## Template Features

The Admin template editor supports:

- Plain text body
- HTML body
- Inline image insertion for HTML templates
- Live preview matching the User preview/send rendering

Sent emails include an HTML body, a plain-text fallback, and inline image parts for embedded template images.

## Local Development

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp E:\Git\connectra\.tmp\pytest -p no:cacheprovider
```

Build Admin:

```powershell
cd connectra_admin
..\.venv\Scripts\python.exe -m PyInstaller connectra_admin.spec --noconfirm --clean
```

Build User:

```powershell
cd connectra_user
..\.venv\Scripts\python.exe -m PyInstaller connectra_user.spec --noconfirm --clean
```

## Runtime Data

Runtime data is stored under:

```text
%USERPROFILE%\.connectra
```

This includes local templates, user session state, encrypted mailbox key data, logs, licenses, and imported update packages.

## UAT Notes

The latest verified test run passed:

```text
76 passed
```

See `TESTING.md` for focused UAT scenarios.
