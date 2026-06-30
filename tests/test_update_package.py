"""Tests for signed generic User update packages."""

import pytest


def test_generic_update_package_accepts_eligible_employee(isolated_data_dir, tmp_path):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        write_license_file,
        write_public_key_file,
    )
    from connectra_core.update_package import (
        create_generic_update_package,
        import_generic_update_package,
    )

    write_license_file(
        create_signed_license("user@example.com", "login-pass", employee_id="EMP001"),
        DATA_DIR / LICENSE_FILE_NAME,
    )
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    user_exe = tmp_path / "connectra_user.exe"
    user_exe.write_bytes(b"user exe")
    update_zip = create_generic_update_package(
        tmp_path / "update.zip",
        user_exe,
        ["EMP001", "EMP002"],
        "0.2.0",
    )

    stored_path = import_generic_update_package(update_zip)

    assert stored_path.exists()


def test_generic_update_package_rejects_ineligible_employee(isolated_data_dir, tmp_path):
    from connectra_core.config import DATA_DIR
    from connectra_core.license_auth import (
        LICENSE_FILE_NAME,
        PUBLIC_KEY_FILE_NAME,
        create_signed_license,
        write_license_file,
        write_public_key_file,
    )
    from connectra_core.update_package import (
        UpdatePackageError,
        create_generic_update_package,
        validate_generic_update_package,
    )

    write_license_file(
        create_signed_license("user@example.com", "login-pass", employee_id="EMP999"),
        DATA_DIR / LICENSE_FILE_NAME,
    )
    write_public_key_file(DATA_DIR / PUBLIC_KEY_FILE_NAME)

    user_exe = tmp_path / "connectra_user.exe"
    user_exe.write_bytes(b"user exe")
    update_zip = create_generic_update_package(
        tmp_path / "update.zip",
        user_exe,
        ["EMP001"],
        "0.2.0",
    )

    with pytest.raises(UpdatePackageError, match="not eligible"):
        validate_generic_update_package(update_zip)
