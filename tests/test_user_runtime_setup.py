"""Tests for User app runtime seed-license import."""


def test_runtime_imports_seed_license_with_mailbox_token(isolated_data_dir, tmp_path, monkeypatch):
    import sys

    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        write_license_file,
        write_public_key_file,
    )
    from connectra_user.runtime_setup import initialize_runtime

    app_dir = tmp_path / "package" / "app"
    seed_dir = tmp_path / "package" / "seed"
    app_dir.mkdir(parents=True)
    seed_dir.mkdir()

    runtime_license = DATA_DIR / LICENSE_FILE_NAME
    seed_license = seed_dir / LICENSE_FILE_NAME

    write_license_file(
        create_signed_license("user@example.com", "login-pass"),
        runtime_license,
    )
    write_license_file(
        create_signed_license("user@example.com", "login-pass", "api key with spaces"),
        seed_license,
    )
    write_public_key_file(seed_dir / PUBLIC_KEY_FILE_NAME)

    monkeypatch.setattr(sys, "executable", str(app_dir / "connectra_user.exe"))

    initialize_runtime()

    assert "mailbox_password_token" in runtime_license.read_text(encoding="utf-8")
