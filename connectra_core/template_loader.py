"""Template loading helpers for runtime and bundled fallback templates."""

import json
from pathlib import Path

from connectra_core.config import TEMPLATE_DIR


def _candidate_template_dirs() -> list[Path]:
    """Return runtime templates first, then bundled fallback templates."""
    repo_root = Path(__file__).resolve().parent.parent
    return [
        TEMPLATE_DIR,
        repo_root / "connectra_user" / "templates",
        repo_root / "connectra_admin" / "templates",
    ]


def load_templates():
    """Load email templates without depending on the current working directory."""
    templates = []

    template_dir = next(
        (path for path in _candidate_template_dirs() if any(path.glob("*.json"))),
        TEMPLATE_DIR,
    )

    if not template_dir.exists():
        return templates

    for path in sorted(template_dir.glob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            body = data.get("body", "")
            data.setdefault("plain_body", "" if body.lstrip().startswith("<") else body)
            data.setdefault("html_body", body if body.lstrip().startswith("<") else "")
            data.setdefault("body", data.get("html_body") or data.get("plain_body") or body)
            templates.append(data)

    return templates
