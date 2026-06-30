"""Signed generic User app update package creation and validation."""

import base64
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from connectra_core import config
from connectra_core.license_auth import (
    PUBLIC_KEY_FILE_NAME,
    _load_private_key,
    get_installed_identity,
)
from connectra_core.version import APP_VERSION

MANIFEST_FILE_NAME = "connectra_update_manifest.json"
SIGNATURE_FILE_NAME = "connectra_update_signature.txt"
USER_EXE_FILE_NAME = "connectra_user.exe"
POLICY_SCHEMA_VERSION = 1


class UpdatePackageError(RuntimeError):
    """Raised when a generic update package cannot be accepted."""


def create_generic_update_package(
    output_zip_path: str | Path,
    user_exe_path: str | Path,
    eligible_employee_ids: list[str],
    version: str,
    release_notes: str = "",
) -> Path:
    """Create a signed generic update package for eligible employees."""
    output_zip_path = Path(output_zip_path)
    user_exe_path = Path(user_exe_path)

    if not user_exe_path.exists():
        raise FileNotFoundError(f"Missing User EXE: {user_exe_path}")

    employee_ids = sorted({employee_id.strip() for employee_id in eligible_employee_ids if employee_id.strip()})
    if not employee_ids:
        raise ValueError("At least one eligible employee ID is required.")

    exe_bytes = user_exe_path.read_bytes()
    manifest = {
        "package_type": "connectra_user_update",
        "user_app_version": version,
        "minimum_user_app_version": APP_VERSION,
        "policy_schema_version": POLICY_SCHEMA_VERSION,
        "eligible_employee_ids": employee_ids,
        "user_exe": USER_EXE_FILE_NAME,
        "sha256": hashlib.sha256(exe_bytes).hexdigest(),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "release_notes": release_notes,
    }
    manifest_bytes = _canonical_json(manifest)
    signature = _load_private_key().sign(manifest_bytes)

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_FILE_NAME, json.dumps(manifest, indent=2))
        zf.writestr(SIGNATURE_FILE_NAME, base64.b64encode(signature).decode("utf-8"))
        zf.write(user_exe_path, USER_EXE_FILE_NAME)

    return output_zip_path


def validate_generic_update_package(package_path: str | Path) -> dict:
    """Validate a generic update package for this installed employee identity."""
    package_path = Path(package_path)
    identity = get_installed_identity()
    employee_id = identity.get("employee_id")
    if not employee_id:
        raise UpdatePackageError("No employee ID is installed on this device.")

    with zipfile.ZipFile(package_path) as zf:
        manifest = json.loads(zf.read(MANIFEST_FILE_NAME).decode("utf-8"))
        signature = base64.b64decode(zf.read(SIGNATURE_FILE_NAME).decode("utf-8"))
        exe_bytes = zf.read(manifest.get("user_exe", USER_EXE_FILE_NAME))

    _verify_manifest_signature(manifest, signature)

    if manifest.get("package_type") != "connectra_user_update":
        raise UpdatePackageError("This is not a Connectra User update package.")
    if manifest.get("policy_schema_version") != POLICY_SCHEMA_VERSION:
        raise UpdatePackageError("This update package format is not supported by this app.")
    if employee_id not in manifest.get("eligible_employee_ids", []):
        raise UpdatePackageError("This employee ID is not eligible for this update package.")
    if hashlib.sha256(exe_bytes).hexdigest() != manifest.get("sha256"):
        raise UpdatePackageError("Update package checksum validation failed.")
    if manifest.get("user_app_version") == APP_VERSION:
        raise UpdatePackageError("This app is already on the same version.")

    return manifest


def import_generic_update_package(package_path: str | Path) -> Path:
    """Validate and store an accepted update package locally for IT/manual install."""
    manifest = validate_generic_update_package(package_path)
    destination_dir = config.RUNTIME_ROOT / "updates"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"connectra_user_update_{manifest['user_app_version']}.zip"
    shutil.copy2(package_path, destination)
    return destination


def _verify_manifest_signature(manifest: dict, signature: bytes) -> None:
    """Verify update manifest signature using the installed Admin public key."""
    public_key_path = config.DATA_DIR / PUBLIC_KEY_FILE_NAME
    if not public_key_path.exists():
        raise UpdatePackageError("Missing Admin public key for update validation.")

    public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
    if not isinstance(public_key, Ed25519PublicKey):
        raise UpdatePackageError("Unsupported Admin public key type.")

    try:
        public_key.verify(signature, _canonical_json(manifest))
    except Exception as exc:
        raise UpdatePackageError("Update package signature validation failed.") from exc


def _canonical_json(payload: dict) -> bytes:
    """Serialize JSON consistently for signing and verification."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
