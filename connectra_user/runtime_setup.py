"""Runtime folder initialization for the User desktop app."""

import json
import shutil
import sys
from pathlib import Path

from connectra_core.config import RUNTIME_ROOT, TEMPLATE_DIR, DATA_DIR, LOG_DIR
from connectra_core.license_auth import LICENSE_FILE_NAME, PUBLIC_KEY_FILE_NAME


def initialize_runtime():
    """Create runtime folders and import installer seed files when present."""
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    import_seed_license()


def import_seed_license() -> bool:
    """Copy adjacent installer seed license files into the runtime data folder."""
    seed_dir = _find_seed_dir()
    if not seed_dir:
        return False

    seed_license = seed_dir / LICENSE_FILE_NAME
    seed_public_key = seed_dir / PUBLIC_KEY_FILE_NAME
    if not seed_license.exists() or not seed_public_key.exists():
        return False

    runtime_license = DATA_DIR / LICENSE_FILE_NAME
    if not _seed_should_replace_runtime(seed_license, runtime_license):
        return False

    shutil.copy2(seed_license, runtime_license)
    shutil.copy2(seed_public_key, DATA_DIR / PUBLIC_KEY_FILE_NAME)
    return True


def _find_seed_dir() -> Path | None:
    """Find seed files beside an extracted installer package."""
    exe_dir = Path(sys.executable).resolve().parent
    module_dir = Path(__file__).resolve().parent

    for base_dir in (exe_dir, exe_dir.parent, module_dir, module_dir.parent):
        seed_dir = base_dir / "seed"
        if seed_dir.exists():
            return seed_dir

    return None


def _seed_should_replace_runtime(seed_license: Path, runtime_license: Path) -> bool:
    """Return True when the seed license is newer or more complete."""
    if not runtime_license.exists():
        return True

    seed_payload = _read_payload(seed_license)
    runtime_payload = _read_payload(runtime_license)

    if seed_payload.get("mailbox_password_token") and not runtime_payload.get("mailbox_password_token"):
        return True

    return seed_license.stat().st_mtime > runtime_license.stat().st_mtime


def _read_payload(license_path: Path) -> dict:
    """Read a license payload, returning an empty payload on invalid files."""
    try:
        license_doc = json.loads(license_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    payload = license_doc.get("payload", {})
    if isinstance(payload, dict):
        return payload

    return {}
