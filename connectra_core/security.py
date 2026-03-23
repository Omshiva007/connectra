"""Password encryption/decryption helpers for Connectra.

Uses the `cryptography` package (Fernet symmetric encryption).  A secret key
is read from the ``CONNECTRA_SECRET_KEY`` environment variable.  If the
variable is not set a deterministic *development-only* key is derived so that
the application still starts without additional configuration, but a warning
is logged to stderr in that case.

Production deployments **must** set a proper ``CONNECTRA_SECRET_KEY``.
"""

import base64
import os
import sys

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover – optional dependency at runtime
    Fernet = None  # type: ignore[assignment,misc]
    InvalidToken = Exception  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

_DEV_KEY = base64.urlsafe_b64encode(b"connectra-dev-key-NOT-FOR-PROD!!")

_fernet_instance: "Fernet | None" = None


def _get_fernet() -> "Fernet":
    """Return a cached Fernet instance, initialising it on first call."""
    global _fernet_instance  # noqa: PLW0603

    if _fernet_instance is not None:
        return _fernet_instance

    if Fernet is None:  # pragma: no cover
        raise ImportError(
            "The 'cryptography' package is required for password encryption. "
            "Install it with: pip install cryptography"
        )

    raw_key = os.environ.get("CONNECTRA_SECRET_KEY", "")

    if raw_key:
        key = raw_key.encode() if isinstance(raw_key, str) else raw_key
    else:
        print(
            "WARNING: CONNECTRA_SECRET_KEY is not set. "
            "Using development key – NOT safe for production.",
            file=sys.stderr,
        )
        key = _DEV_KEY

    _fernet_instance = Fernet(key)
    return _fernet_instance


def reset_fernet() -> None:
    """Reset the cached Fernet instance (useful in tests)."""
    global _fernet_instance  # noqa: PLW0603
    _fernet_instance = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encrypt_password(plain_text: str) -> str:
    """Encrypt *plain_text* and return a URL-safe base64 token string."""
    if not isinstance(plain_text, str):
        raise TypeError("plain_text must be a str")
    if not plain_text:
        raise ValueError("plain_text must not be empty")

    fernet = _get_fernet()
    token = fernet.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(token: str) -> str:
    """Decrypt a token previously produced by :func:`encrypt_password`.

    Raises :class:`ValueError` if the token is invalid or was encrypted with
    a different key.
    """
    if not isinstance(token, str):
        raise TypeError("token must be a str")
    if not token:
        raise ValueError("token must not be empty")

    fernet = _get_fernet()
    try:
        plain = fernet.decrypt(token.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid or corrupted password token") from exc
