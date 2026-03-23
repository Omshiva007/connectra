# Connectra Testing Guide

This document explains how to run the Connectra test suite locally and interpret the results.

## Prerequisites

Install the project dependencies (including test and security extras):

```bash
pip install -r requirements.txt
```

The test suite requires:
- **pytest** – test runner
- **pytest-cov** – coverage reporting
- **cryptography** – for `connectra_core/security.py` (password encryption tests)
- **python-dotenv** – environment variable loading

## Running Tests

### Run All Tests

```bash
pytest
```

Or equivalently:

```bash
python -m pytest tests/
```

### Run a Specific Test File

```bash
pytest tests/test_validators.py
pytest tests/test_security.py
```

### Run a Specific Test Class or Function

```bash
pytest tests/test_database.py::TestGetConnection
pytest tests/test_holiday_checker.py::TestCheckUpcomingHolidays::test_returns_holiday_on_reminder_date
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Short Traceback

```bash
pytest --tb=short
```

## Coverage Reports

### Terminal Coverage Summary

```bash
pytest --cov=connectra_core --cov-report=term-missing
```

### HTML Coverage Report

```bash
pytest --cov=connectra_core --cov-report=html
# Open htmlcov/index.html in your browser
```

## Environment Variables

The tests use **isolated temporary databases** and mock SMTP – no real credentials are needed.

For password encryption tests, the `CONNECTRA_SECRET_KEY` environment variable controls the Fernet key.  If it is not set, a development-only fallback key is used and a warning is printed to stderr (this is expected in tests).

To use a specific key during testing:

```bash
CONNECTRA_SECRET_KEY="<base64-url-safe-32-byte-key>" pytest
```

Generate a valid key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures, factory helpers, DB setup
├── test_database.py         # connectra_core/database.py – user DB operations
├── test_admin_database.py   # connectra_core/admin_database.py – admin DB
├── test_holiday_checker.py  # connectra_core/holiday_checker.py
├── test_filters.py          # connectra_core/filters.py – email filtering
├── test_email_sender.py     # connectra_core/email_sender.py – SMTP & logging
├── test_validators.py       # connectra_core/validators.py – input validation
└── test_security.py         # connectra_core/security.py – password encryption
```

## Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `user_db_conn` | Isolated WAL-mode SQLite DB for user-side tests. Patches `database.get_connection` and `email_sender.get_connection`. Yields an open connection for assertions. |
| `admin_db_conn` | Isolated WAL-mode SQLite DB for admin-side and holiday-checker tests. Patches `admin_database.get_connection` and `holiday_checker.get_connection`. Also patches `ADMIN_DB.exists()` so the guard never short-circuits. |
| `mock_smtp` | Patches `smtplib.SMTP` with a `MagicMock`. Yields `(mock_cls, mock_server)`. |
| `template_dir` | Creates a `tmp_path/templates/` directory with a sample JSON template. |

### Factory Helpers

`conftest.py` also exports reusable factory functions for creating test data:

```python
from tests.conftest import make_user, make_holiday, make_contact

user    = make_user(email="alice@example.com", password="app_pass")
holiday = make_holiday(holiday="Easter", date="2026-04-05", reminder_days=7)
contact = make_contact(email="client@acme.com", domain="acme.com")
```

## What Each Test Module Covers

### `test_database.py`
- Tables are created on first connection
- UNIQUE constraints on `clients.domain` and `contacts.email`
- Inserting and retrieving email log entries
- `initialize_database()` is idempotent
- No hardcoded `C:/Connectra` path remains in the source

### `test_admin_database.py`
- `users` and `settings` tables are created
- UNIQUE constraint on `users.email`
- `get_setting()` / `set_setting()` round-trip, including overwrite
- No hardcoded `C:/Connectra` path remains

### `test_holiday_checker.py`
- Returns holidays whose reminder date equals today
- Skips future holidays (reminder date in the future)
- Skips inactive holidays (`active=0`)
- Parses `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`, and `Month DD, YYYY` date formats
- Gracefully skips rows with bad or `NULL` dates

### `test_filters.py`
- Correctly identifies internal company email addresses
- Correctly identifies external client email addresses
- Handles always-internal domains (`zoom.us`, `otter.ai`, etc.)
- Handles always-internal domain suffixes (`atlassian.net`, etc.)
- Handles edge cases (empty string, `None`, malformed addresses)

### `test_email_sender.py`
- `log_email()` inserts a row into the `email_logs` table
- Timestamp is stored in ISO 8601 format
- Backend HTTP call is best-effort (failures are silenced)
- `send_email()` calls `starttls()`, `login()`, `sendmail()`, and `quit()`
- Single and multiple recipients are handled correctly

### `test_validators.py`
- Valid and invalid email address formats
- Template name / subject / body validation (length limits, empty checks)
- Contact email + domain pair validation
- Holiday entry validation (date formats, reminder days range)

### `test_security.py`
- `encrypt_password()` / `decrypt_password()` round-trip
- Each encryption produces a unique token (random IV)
- Tokens from a different key cannot be decrypted
- Empty or non-string inputs raise appropriate exceptions
- Unicode and long passwords survive the round-trip
- Warning is printed to stderr when `CONNECTRA_SECRET_KEY` is not set

## Troubleshooting

### `ModuleNotFoundError: No module named 'connectra_core'`

Run pytest from the repository root:

```bash
cd /path/to/connectra
pytest
```

`conftest.py` adds the repository root to `sys.path` automatically.

### `ImportError: No module named 'cryptography'`

Install the missing dependency:

```bash
pip install cryptography
```

### `ValueError: Fernet key must be 32 url-safe base64-encoded bytes.`

Your `CONNECTRA_SECRET_KEY` environment variable is set to an invalid value.  Either unset it (the tests will use the development fallback) or generate a fresh key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Tests pass locally but fail in CI

Check that the CI environment has all dependencies installed:

```bash
pip install pytest pytest-cov cryptography python-dotenv
```

Ensure the `CONNECTRA_SECRET_KEY` variable (if set in CI secrets) is a valid Fernet key.
