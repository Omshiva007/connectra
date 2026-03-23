"""
Tests for connectra_core.security (Fernet password encryption).
"""
import pytest


def test_encrypt_returns_string(isolated_data_dir):
    """encrypt_password must return a non-empty string."""
    from connectra_core.security import encrypt_password
    result = encrypt_password("my_secret_password")
    assert isinstance(result, str)
    assert len(result) > 0


def test_encrypted_differs_from_plain(isolated_data_dir):
    """Encrypted password must not equal the original."""
    from connectra_core.security import encrypt_password
    plain = "my_secret_password"
    assert encrypt_password(plain) != plain


def test_round_trip(isolated_data_dir):
    """Decrypting an encrypted password must return the original."""
    from connectra_core.security import encrypt_password, decrypt_password
    plain = "super_secret_123!"
    assert decrypt_password(encrypt_password(plain)) == plain


def test_different_ciphertexts_for_same_input(isolated_data_dir):
    """Fernet includes a nonce, so two encryptions of the same plaintext differ."""
    from connectra_core.security import encrypt_password
    plain = "password"
    assert encrypt_password(plain) != encrypt_password(plain)


def test_invalid_token_raises_value_error(isolated_data_dir):
    """decrypt_password must raise ValueError for garbage input."""
    from connectra_core.security import decrypt_password
    with pytest.raises(ValueError):
        decrypt_password("this-is-not-a-valid-fernet-token")


def test_key_file_created(isolated_data_dir):
    """A key file must be created under RUNTIME_ROOT when no env var is set."""
    from connectra_core.security import encrypt_password, _KEY_FILE
    encrypt_password("trigger_key_creation")
    assert _KEY_FILE.exists()


def test_env_var_key_used(isolated_data_dir, monkeypatch):
    """When CONNECTRA_SECRET_KEY is set the env-var key must be used."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CONNECTRA_SECRET_KEY", key)

    import importlib
    import connectra_core.security as sec
    importlib.reload(sec)

    cipher = sec.encrypt_password("hello")
    assert sec.decrypt_password(cipher) == "hello"
