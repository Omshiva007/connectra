"""Local User app credential and session storage."""

import json
from pathlib import Path

from connectra_core.config import DATA_DIR
from connectra_core.security import decrypt_password, encrypt_password

LOCAL_CREDENTIALS_FILE = "connectra_local_credentials.json"
SESSION_FILE = "connectra_session.json"


def _credentials_path() -> Path:
    """Return the local encrypted credential file path."""
    return DATA_DIR / LOCAL_CREDENTIALS_FILE


def _session_path() -> Path:
    """Return the local signed-in session file path."""
    return DATA_DIR / SESSION_FILE


def save_mailbox_key(email: str, mailbox_key: str) -> None:
    """Store a user's mailbox key locally after connectivity validation."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "email": email.strip().lower(),
        "mailbox_key": encrypt_password(mailbox_key),
    }
    _credentials_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_mailbox_key(email: str) -> str | None:
    """Return the local mailbox key for *email* when present and decryptable."""
    path = _credentials_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("email") != email.strip().lower():
        return None

    encrypted_key = payload.get("mailbox_key")
    if not encrypted_key:
        return None

    try:
        return decrypt_password(encrypted_key)
    except ValueError:
        return None


def has_mailbox_key(email: str) -> bool:
    """Return True when a local mailbox key is available for *email*."""
    return bool(load_mailbox_key(email))


def save_session(email: str) -> None:
    """Persist the signed-in user email until explicit logout."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"email": email.strip().lower()}
    _session_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session() -> str | None:
    """Return the signed-in email if a session exists."""
    path = _session_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    email = payload.get("email")
    if isinstance(email, str) and email.strip():
        return email.strip().lower()

    return None


def clear_session() -> None:
    """Clear the persisted signed-in session."""
    path = _session_path()
    if path.exists():
        path.unlink()
