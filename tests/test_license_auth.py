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
