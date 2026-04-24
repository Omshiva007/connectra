import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from connectra_core.config import DATA_DIR, RUNTIME_ROOT

LICENSE_FILE_NAME = "connectra_user_license.json"
PUBLIC_KEY_FILE_NAME = "connectra_license_public_key.pem"
_PRIVATE_KEY_PATH = RUNTIME_ROOT / "keys" / "connectra_license_private_key.pem"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pbkdf2_hash(passcode: str, salt_b64: str) -> str:
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    digest = hashlib.pbkdf2_hmac("sha256", passcode.encode("utf-8"), salt, 200_000)
    return base64.b64encode(digest).decode("utf-8")


def _verify_passcode(passcode: str, salt_b64: str, expected_hash_b64: str) -> bool:
    actual = _pbkdf2_hash(passcode, salt_b64)
    return hmac.compare_digest(actual, expected_hash_b64)


def ensure_signing_keypair() -> tuple[bytes, bytes]:
    if _PRIVATE_KEY_PATH.exists():
        private_key = serialization.load_pem_private_key(
            _PRIVATE_KEY_PATH.read_bytes(),
            password=None,
        )
        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Unexpected private key type for Connectra license signing.")
    else:
        _PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        _PRIVATE_KEY_PATH.write_bytes(
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
    return _PRIVATE_KEY_PATH.read_bytes(), public_key_pem


def _load_private_key() -> Ed25519PrivateKey:
    ensure_signing_keypair()
    private_key = serialization.load_pem_private_key(
        _PRIVATE_KEY_PATH.read_bytes(),
        password=None,
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Unexpected private key type for Connectra license signing.")
    return private_key


def create_signed_license(email: str, passcode: str) -> dict:
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

    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = _load_private_key().sign(payload_bytes)

    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("utf-8"),
        "algorithm": "ed25519",
    }


def write_license_file(license_doc: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(license_doc, indent=2), encoding="utf-8")


def write_public_key_file(output_path: Path) -> None:
    _, public_pem = ensure_signing_keypair()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(public_pem)


def verify_local_login(email: str, passcode: str) -> tuple[bool, str]:
    data_dir = DATA_DIR
    license_path = data_dir / LICENSE_FILE_NAME
    public_key_path = data_dir / PUBLIC_KEY_FILE_NAME

    if not license_path.exists():
        return False, f"Missing license file: {license_path}"
    if not public_key_path.exists():
        return False, f"Missing public key file: {public_key_path}"

    try:
        license_doc = json.loads(license_path.read_text(encoding="utf-8"))
        payload = license_doc["payload"]
        signature_b64 = license_doc["signature"]
    except Exception as exc:
        return False, f"Invalid license format: {exc}"

    try:
        public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
        if not isinstance(public_key, Ed25519PublicKey):
            return False, "Unsupported public key type."

        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(signature, payload_bytes)
    except Exception as exc:
        return False, f"License signature validation failed: {exc}"

    expected_email = payload.get("email", "")
    if email.strip().lower() != expected_email:
        return False, "Email does not match this licensed build."

    if not _verify_passcode(passcode, payload.get("passcode_salt", ""), payload.get("passcode_hash", "")):
        return False, "Invalid passcode."

    return True, "ok"
