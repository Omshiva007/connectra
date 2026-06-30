"""Admin-controlled update metadata and installer download helpers."""

from dataclasses import dataclass
from pathlib import Path
import urllib.error
import urllib.request

from connectra_core.admin_database import get_setting
from connectra_core.config import RUNTIME_ROOT
from connectra_core.version import APP_VERSION


@dataclass(frozen=True)
class UpdateInfo:
    """Resolved update state shown to the user app."""

    current_version: str
    available_version: str
    approved_version: str
    release_notes: str
    installer_url: str

    @property
    def is_update_available(self) -> bool:
        """True only after admin approves a version newer than this app."""
        return bool(self.approved_version and self.approved_version != self.current_version)


def get_update_info() -> UpdateInfo:
    """Load update metadata from the shared admin settings database."""
    return UpdateInfo(
        current_version=APP_VERSION,
        available_version=get_setting("available_version") or "",
        approved_version=get_setting("approved_version") or "",
        release_notes=get_setting("release_notes") or "",
        installer_url=get_setting("installer_url") or "",
    )


def download_approved_update(destination_dir: Path | None = None) -> Path:
    """Download the admin-approved installer to the local updates folder."""
    info = get_update_info()
    if not info.is_update_available:
        raise ValueError("No approved update is available.")
    if not info.installer_url:
        raise ValueError("No installer URL is configured for the approved update.")

    destination_dir = destination_dir or (RUNTIME_ROOT / "updates")
    destination_dir.mkdir(parents=True, exist_ok=True)

    filename = info.installer_url.rstrip("/").split("/")[-1] or "connectra_update.zip"
    output_path = destination_dir / filename

    try:
        urllib.request.urlretrieve(info.installer_url, output_path)
    except (urllib.error.URLError, ValueError) as exc:
        raise RuntimeError(f"Failed to download update: {exc}") from exc

    return output_path
