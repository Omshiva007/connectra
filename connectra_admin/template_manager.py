"""Admin template file operations and publish-to-runtime sync."""

import json
import shutil
from pathlib import Path

from connectra_core.config import TEMPLATE_DIR

ADMIN_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
RUNTIME_TEMPLATE_DIR = TEMPLATE_DIR


def ensure_dirs():
    """Create both admin template and runtime template directories."""
    ADMIN_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def list_templates():
    """Return available admin template names without file extensions."""
    ensure_dirs()

    templates = []

    for path in sorted(ADMIN_TEMPLATE_DIR.glob("*.json")):
        templates.append(path.stem)

    return templates


def load_template(name):
    """Load one admin-managed template JSON document by name."""
    path = ADMIN_TEMPLATE_DIR / f"{name}.json"

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    body = data.get("body", "")
    data.setdefault("plain_body", "" if body.lstrip().startswith("<") else body)
    data.setdefault("html_body", body if body.lstrip().startswith("<") else "")
    data.setdefault("body", data.get("html_body") or data.get("plain_body") or body)
    return data


def save_template(name, subject, plain_body="", html_body=""):
    """Persist a template JSON file edited in the Admin app."""
    ensure_dirs()

    path = ADMIN_TEMPLATE_DIR / f"{name}.json"
    body = html_body or plain_body

    data = {
        "name": name,
        "subject": subject,
        "plain_body": plain_body,
        "html_body": html_body,
        "body": body,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def delete_template(name):
    """Delete an admin template when it exists."""
    path = ADMIN_TEMPLATE_DIR / f"{name}.json"

    if path.exists():
        path.unlink()


def publish_templates():
    """Copy admin-approved templates into the runtime folder for user apps."""
    ensure_dirs()

    for src in ADMIN_TEMPLATE_DIR.glob("*.json"):
        shutil.copy(src, RUNTIME_TEMPLATE_DIR / src.name)
