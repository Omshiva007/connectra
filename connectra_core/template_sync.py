"""Template seeding helpers for first-run user profiles."""

import shutil
from pathlib import Path

from connectra_core.config import TEMPLATE_DIR


def _source_template_dirs() -> list[Path]:
    """Return bundled template folders used to seed a new runtime profile."""
    repo_root = Path(__file__).resolve().parent.parent
    return [
        repo_root / "connectra_admin" / "templates",
        repo_root / "connectra_user" / "templates",
    ]


def sync_templates():
    """Refresh runtime templates from available admin-managed source templates."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    sources = [
        path
        for folder in _source_template_dirs()
        if folder.exists()
        for path in folder.glob("*.json")
    ]

    if not sources:
        return

    for src in sources:
        destination = TEMPLATE_DIR / src.name
        if (
            not destination.exists()
            or src.stat().st_mtime_ns > destination.stat().st_mtime_ns
            or src.read_bytes() != destination.read_bytes()
        ):
            shutil.copy2(src, destination)
