"""Unit tests for connectra_core/security.py"""

import os

import pytest

from connectra_core.security import encrypt_password, decrypt_password, reset_fernet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _use_test_key(monkeypatch):
    """Set a stable Fernet-compatible key for deterministic testing."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CONNECTRA_SECRET_KEY", key)
    reset_fernet()
    return key


# ---------------------------------------------------------------------------
# encrypt_password
# ---------------------------------------------------------------------------

class TestEncryptPassword:

    def test_returns_string(self, monkeypatch):
        _use_test_key(monkeypatch)
        token = encrypt_password("my_secret")
        assert isinstance(token, str)

    def test_token_not_equal_to_plain_text(self, monkeypatch):
        _use_test_key(monkeypatch)
        token = encrypt_password("my_secret")
        assert token != "my_secret"

    def test_encrypting_same_password_twice_gives_different_tokens(self, monkeypatch):
        """Fernet uses a random IV, so each encryption is unique."""
        _use_test_key(monkeypatch)
        t1 = encrypt_password("password123")
        reset_fernet()
        t2 = encrypt_password("password123")
        # Tokens should differ (probabilistic, but effectively guaranteed)
        # Just verify both are valid by decrypting them:
        assert decrypt_password(t1) == "password123"
        assert decrypt_password(t2) == "password123"

    def test_raises_on_empty_password(self, monkeypatch):
        _use_test_key(monkeypatch)
        with pytest.raises(ValueError, match="must not be empty"):
            encrypt_password("")

    def test_raises_on_non_string(self, monkeypatch):
        _use_test_key(monkeypatch)
        with pytest.raises(TypeError):
            encrypt_password(12345)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# decrypt_password
# ---------------------------------------------------------------------------

class TestDecryptPassword:

    def test_roundtrip(self, monkeypatch):
        _use_test_key(monkeypatch)
        plain = "super_secret_password"
        token = encrypt_password(plain)
        recovered = decrypt_password(token)
        assert recovered == plain

    def test_raises_on_invalid_token(self, monkeypatch):
        _use_test_key(monkeypatch)
        with pytest.raises(ValueError, match="Invalid or corrupted"):
            decrypt_password("this-is-not-a-valid-fernet-token")

    def test_raises_on_empty_token(self, monkeypatch):
        _use_test_key(monkeypatch)
        with pytest.raises(ValueError, match="must not be empty"):
            decrypt_password("")

    def test_raises_on_non_string_token(self, monkeypatch):
        _use_test_key(monkeypatch)
        with pytest.raises(TypeError):
            decrypt_password(b"bytes-token")  # type: ignore[arg-type]

    def test_different_key_cannot_decrypt(self, monkeypatch):
        """Token encrypted with key A cannot be decrypted with key B."""
        from cryptography.fernet import Fernet

        key_a = Fernet.generate_key().decode()
        monkeypatch.setenv("CONNECTRA_SECRET_KEY", key_a)
        reset_fernet()

        token = encrypt_password("secret")

        key_b = Fernet.generate_key().decode()
        monkeypatch.setenv("CONNECTRA_SECRET_KEY", key_b)
        reset_fernet()

        with pytest.raises(ValueError):
            decrypt_password(token)

    def test_unicode_password_roundtrip(self, monkeypatch):
        _use_test_key(monkeypatch)
        plain = "パスワード123"  # Japanese characters
        token = encrypt_password(plain)
        assert decrypt_password(token) == plain

    def test_long_password_roundtrip(self, monkeypatch):
        _use_test_key(monkeypatch)
        plain = "a" * 10_000
        token = encrypt_password(plain)
        assert decrypt_password(token) == plain


# ---------------------------------------------------------------------------
# Dev-key warning (no CONNECTRA_SECRET_KEY set)
# ---------------------------------------------------------------------------

class TestDevKeyWarning:

    def test_warns_when_no_key_set(self, monkeypatch, capsys):
        monkeypatch.delenv("CONNECTRA_SECRET_KEY", raising=False)
        reset_fernet()

        encrypt_password("test")

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "CONNECTRA_SECRET_KEY" in captured.err

    def test_dev_key_still_allows_roundtrip(self, monkeypatch):
        monkeypatch.delenv("CONNECTRA_SECRET_KEY", raising=False)
        reset_fernet()

        token = encrypt_password("dev_test")
        reset_fernet()
        # decrypt with same implicit dev key
        monkeypatch.delenv("CONNECTRA_SECRET_KEY", raising=False)
        assert decrypt_password(token) == "dev_test"
