"""
Password encryption/decryption using Fernet (AES-128-CBC with HMAC-SHA256).

The encryption key is resolved in this priority order:
1. CONNECTRA_SECRET_KEY environment variable (base64-url-encoded 32-byte key)
2. Key file stored at <RUNTIME_ROOT>/.secret_key
3. A new key is generated, saved to the key file, and reused on subsequent runs.
"""
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from connectra_core.config import RUNTIME_ROOT


_KEY_FILE: Path = RUNTIME_ROOT / ".secret_key"
_fernet_instance: Fernet | None = None


def _load_or_create_key() -> bytes:
    """Return an existing Fernet key or generate and persist a new one."""
    env_key = os.environ.get("CONNECTRA_SECRET_KEY")
    if env_key:
        return env_key.encode()

    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()

    # Generate a new key and save it for future runs.
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    return key


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_load_or_create_key())
    return _fernet_instance


def encrypt_password(plain_text: str) -> str:
    """Encrypt *plain_text* and return a URL-safe base64-encoded ciphertext string."""
    token = _get_fernet().encrypt(plain_text.encode())
    return token.decode()


def decrypt_password(cipher_text: str) -> str:
    """Decrypt *cipher_text* and return the original plain-text password.

    Raises ``ValueError`` if the token is invalid or was encrypted with a
    different key.
    """
    try:
        return _get_fernet().decrypt(cipher_text.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt password: invalid token or wrong key") from exc
