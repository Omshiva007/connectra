"""Create versioned release ZIPs from built Connectra desktop executables."""

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def create_release_package(
    output_zip_path: str | Path,
    version: str,
    user_exe: str | Path,
    admin_exe: str | Path,
) -> Path:
    """Package user/admin EXEs with a manifest for manual release hosting."""
    output_zip_path = Path(output_zip_path)
    user_exe = Path(user_exe)
    admin_exe = Path(admin_exe)

    if not version:
        raise ValueError("Version is required.")
    if not user_exe.exists():
        raise FileNotFoundError(f"Missing user EXE: {user_exe}")
    if not admin_exe.exists():
        raise FileNotFoundError(f"Missing admin EXE: {admin_exe}")

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": version,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": {
            "user_app": user_exe.name,
            "admin_app": admin_exe.name,
        },
        "notes": "Upload this ZIP to the configured installer URL for admin-approved rollout.",
    }

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(user_exe, user_exe.name)
        zf.write(admin_exe, admin_exe.name)
        zf.writestr("release_manifest.json", json.dumps(manifest, indent=2))

    return output_zip_path


def create_release_from_repo(repo_root: str | Path, version: str) -> Path:
    """Package the standard dist outputs under a repo-local releases folder."""
    repo_root = Path(repo_root)
    release_dir = repo_root / "releases"
    output_zip_path = release_dir / f"connectra-{version}.zip"

    return create_release_package(
        output_zip_path=output_zip_path,
        version=version,
        user_exe=repo_root / "connectra_user" / "dist" / "connectra_user.exe",
        admin_exe=repo_root / "connectra_admin" / "dist" / "connectra_admin.exe",
    )
