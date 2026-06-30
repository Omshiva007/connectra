"""
Tests for local signed-license authentication.
"""

def test_license_round_trip_success(isolated_data_dir):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        verify_local_login,
        write_license_file,
        write_public_key_file,
    )

    email = "user@example.com"
    passcode = "passcode-123"

    write_license_file(create_signed_license(email, passcode), DATA_DIR / LICENSE_FILE_NAME)
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    ok, msg = verify_local_login(email, passcode)
    assert ok is True
    assert msg == "ok"


def test_license_mailbox_password_unlocks_after_login(isolated_data_dir):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        get_mailbox_password,
        write_license_file,
        write_public_key_file,
    )

    email = "user@example.com"
    passcode = "login-passcode"
    mailbox_password = "email-app-key"

    license_doc = create_signed_license(email, passcode, mailbox_password)
    write_license_file(license_doc, DATA_DIR / LICENSE_FILE_NAME)
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    ok, msg, unlocked_password = get_mailbox_password(email, passcode)

    assert ok is True
    assert msg == "ok"
    assert unlocked_password == mailbox_password
    assert mailbox_password not in (DATA_DIR / LICENSE_FILE_NAME).read_text(encoding="utf-8")


def test_license_without_mailbox_password_requests_rebuild(isolated_data_dir):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        get_mailbox_password,
        write_license_file,
        write_public_key_file,
    )

    email = "user@example.com"
    passcode = "login-passcode"

    write_license_file(create_signed_license(email, passcode), DATA_DIR / LICENSE_FILE_NAME)
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    ok, msg, unlocked_password = get_mailbox_password(email, passcode)

    assert ok is False
    assert "rebuild" in msg.lower()
    assert unlocked_password is None


def test_license_rejects_wrong_email_or_passcode(isolated_data_dir):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        verify_local_login,
        write_license_file,
        write_public_key_file,
    )

    email = "user@example.com"
    passcode = "passcode-123"

    write_license_file(create_signed_license(email, passcode), DATA_DIR / LICENSE_FILE_NAME)
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    ok_email, _ = verify_local_login("other@example.com", passcode)
    ok_pass, _ = verify_local_login(email, "wrong-passcode")

    assert ok_email is False
    assert ok_pass is False


def test_license_hash_fallback_without_hashlib_pbkdf2(isolated_data_dir, monkeypatch):
    import hashlib

    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        verify_local_login,
        write_license_file,
        write_public_key_file,
    )

    monkeypatch.delattr(hashlib, "pbkdf2_hmac", raising=False)

    email = "user@example.com"
    passcode = "passcode-123"

    write_license_file(create_signed_license(email, passcode), DATA_DIR / LICENSE_FILE_NAME)
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    ok, msg = verify_local_login(email, passcode)
    assert ok is True
    assert msg == "ok"
