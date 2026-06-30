"""Signed local license creation and verification for user app bundles."""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from connectra_core import config

LICENSE_FILE_NAME = "connectra_user_license.json"
PUBLIC_KEY_FILE_NAME = "connectra_license_public_key.pem"


def _data_dir() -> Path:
    """Return the currently configured runtime data directory."""
    return config.DATA_DIR


def _private_key_path() -> Path:
    """Return the currently configured private license-signing key path."""
    return config.RUNTIME_ROOT / "keys" / "connectra_license_private_key.pem"


def _utc_now_iso() -> str:
    """Return a compact UTC timestamp for license payloads."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pbkdf2_hash(passcode: str, salt_b64: str) -> str:
    """Hash a passcode with PBKDF2 so plaintext passcodes are never stored."""
    digest = _pbkdf2_bytes(passcode, salt_b64)
    return base64.b64encode(digest).decode("utf-8")


def _pbkdf2_bytes(passcode: str, salt_b64: str) -> bytes:
    """Derive bytes from a passcode for hashing and license secret encryption."""
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    passcode_bytes = passcode.encode("utf-8")

    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac("sha256", passcode_bytes, salt, 200_000)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return kdf.derive(passcode_bytes)


def _fernet_for_passcode(passcode: str, salt_b64: str) -> Fernet:
    """Create a Fernet cipher from the user's passcode and license salt."""
    key = base64.urlsafe_b64encode(_pbkdf2_bytes(passcode, salt_b64))
    return Fernet(key)


def _encrypt_mailbox_password(mailbox_password: str, passcode: str, salt_b64: str) -> str:
    """Encrypt a mailbox app password so it is not stored as plaintext."""
    token = _fernet_for_passcode(passcode, salt_b64).encrypt(
        mailbox_password.encode("utf-8")
    )
    return token.decode("utf-8")


def _decrypt_mailbox_password(token: str, passcode: str, salt_b64: str) -> str:
    """Decrypt the mailbox app password embedded in a signed license."""
    decrypted = _fernet_for_passcode(passcode, salt_b64).decrypt(token.encode("utf-8"))
    return decrypted.decode("utf-8")


def _verify_passcode(passcode: str, salt_b64: str, expected_hash_b64: str) -> bool:
    """Compare a passcode against the stored PBKDF2 hash safely."""
    actual = _pbkdf2_hash(passcode, salt_b64)
    return hmac.compare_digest(actual, expected_hash_b64)


def ensure_signing_keypair() -> tuple[bytes, bytes]:
    """Create or load the Ed25519 keypair used to sign user licenses."""
    private_key_path = _private_key_path()

    if private_key_path.exists():
        private_key = serialization.load_pem_private_key(
            private_key_path.read_bytes(),
            password=None,
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Unexpected private key type for Connectra license signing.")
    else:
        private_key_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        private_key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key_path.read_bytes(), public_key_pem


def _load_private_key() -> Ed25519PrivateKey:
    """Load the private signing key after ensuring it exists."""
    ensure_signing_keypair()
    private_key = serialization.load_pem_private_key(
        _private_key_path().read_bytes(),
        password=None,
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Unexpected private key type for Connectra license signing.")
    return private_key


def create_signed_license(
    email: str,
    passcode: str,
    mailbox_password: str | None = None,
    employee_id: str | None = None,
) -> dict:
    """Create a signed license document for one user email and passcode."""
    if not email or not passcode:
        raise ValueError("Email and passcode are required.")

    salt_b64 = base64.b64encode(hashlib.sha256(f"{email}:{_utc_now_iso()}".encode()).digest()[:16]).decode("utf-8")
    payload = {
        "email": email.strip().lower(),
        "passcode_salt": salt_b64,
        "passcode_hash": _pbkdf2_hash(passcode, salt_b64),
        "issued_at": _utc_now_iso(),
        "version": 1,
    }

    if employee_id:
        payload["employee_id"] = employee_id.strip()

    if mailbox_password:
        payload["mailbox_password_token"] = _encrypt_mailbox_password(
            mailbox_password,
            passcode,
            salt_b64,
        )

    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _load_private_key().sign(payload_bytes)

    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("utf-8"),
        "algorithm": "ed25519",
    }


def write_license_file(license_doc: dict, output_path: Path) -> None:
    """Write a generated license document to disk as formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(license_doc, indent=2), encoding="utf-8")


def write_public_key_file(output_path: Path) -> None:
    """Write the public verification key next to a user license bundle."""
    _, public_pem = ensure_signing_keypair()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(public_pem)


def verify_local_login(email: str, passcode: str) -> tuple[bool, str]:
    """Verify license signature, licensed email, and passcode at login."""
    is_valid, message, _ = _verify_local_license(email, passcode)
    return is_valid, message


def get_mailbox_password(email: str, passcode: str) -> tuple[bool, str, str | None]:
    """Return the mailbox app password from a verified local license."""
    is_valid, message, payload = _verify_local_license(email, passcode)
    if not is_valid:
        return False, message, None

    token = payload.get("mailbox_password_token")
    if not token:
        return (
            False,
            "Mailbox key is missing from this user package. Ask admin to rebuild the installer.",
            None,
        )

    try:
        mailbox_password = _decrypt_mailbox_password(
            token,
            passcode,
            payload.get("passcode_salt", ""),
        )
    except (InvalidToken, ValueError) as exc:
        return False, f"Mailbox key could not be unlocked: {exc}", None

    return True, "ok", mailbox_password


def get_local_identity(email: str, passcode: str) -> tuple[bool, str, dict]:
    """Return signed local identity payload after email/passcode validation."""
    return _verify_local_license(email, passcode)


def get_installed_identity() -> dict:
    """Return the installed identity payload without validating passcode."""
    license_path = _data_dir() / LICENSE_FILE_NAME
    if not license_path.exists():
        return {}

    try:
        license_doc = json.loads(license_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    payload = license_doc.get("payload", {})
    if isinstance(payload, dict):
        return payload

    return {}


def _verify_local_license(email: str, passcode: str) -> tuple[bool, str, dict]:
    """Verify license signature, email, and passcode, returning the payload."""
    data_dir = _data_dir()
    license_path = data_dir / LICENSE_FILE_NAME
    public_key_path = data_dir / PUBLIC_KEY_FILE_NAME

    if not license_path.exists():
        return False, f"Missing license file: {license_path}", {}
    if not public_key_path.exists():
        return False, f"Missing public key file: {public_key_path}", {}

    try:
        license_doc = json.loads(license_path.read_text(encoding="utf-8"))
        payload = license_doc["payload"]
        signature_b64 = license_doc["signature"]
    except Exception as exc:
        return False, f"Invalid license format: {exc}", {}

    try:
        public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            return False, "Unsupported public key type.", {}

        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(signature, payload_bytes)
    except Exception as exc:
        return False, f"License signature validation failed: {exc}", {}

    expected_email = payload.get("email", "")
    if email.strip().lower() != expected_email:
        return False, "Email does not match this licensed build.", {}

    if not _verify_passcode(passcode, payload.get("passcode_salt", ""), payload.get("passcode_hash", "")):
        return False, "Invalid User App login password. Do not use the mailbox/API key here.", {}

    return True, "ok", payload
