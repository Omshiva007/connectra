from datetime import datetime
import importlib
import json
import zipfile

import pytest


def test_mail_settings_include_provider(isolated_data_dir):
    from connectra_core.admin_database import set_setting
    from connectra_core.mail_settings import get_mail_settings

    set_setting("mail_provider", "microsoft365")
    set_setting("imap_server", "outlook.office365.com")

    settings = get_mail_settings()

    assert settings.provider == "microsoft365"
    assert settings.imap_server == "outlook.office365.com"


def test_mail_settings_provider_preset_defaults(isolated_data_dir):
    from connectra_core.admin_database import set_setting
    from connectra_core.mail_settings import get_mail_settings

    set_setting("mail_provider", "zoho")

    settings = get_mail_settings()

    assert settings.imap_server == "imap.zoho.com"
    assert settings.smtp_server == "smtp.zoho.com"


def test_update_info_detects_admin_approved_update(isolated_data_dir):
    from connectra_core.admin_database import set_setting
    from connectra_core.update_manager import get_update_info

    set_setting("approved_version", "9.9.9")
    set_setting("installer_url", "https://example.com/connectra.zip")
    set_setting("release_notes", "Admin approved build.")

    update_info = get_update_info()

    assert update_info.is_update_available
    assert update_info.installer_url == "https://example.com/connectra.zip"
    assert update_info.release_notes == "Admin approved build."


def test_download_approved_update_uses_installer_url(isolated_data_dir, tmp_path):
    from unittest.mock import patch

    from connectra_core.admin_database import set_setting
    from connectra_core.update_manager import download_approved_update

    set_setting("approved_version", "9.9.9")
    set_setting("installer_url", "https://example.com/connectra.zip")

    with patch("connectra_core.update_manager.urllib.request.urlretrieve") as mock_urlretrieve:
        output_path = download_approved_update(tmp_path)

    assert output_path == tmp_path / "connectra.zip"
    mock_urlretrieve.assert_called_once_with(
        "https://example.com/connectra.zip",
        tmp_path / "connectra.zip",
    )


def test_export_logs_csv_writes_activity_rows(isolated_data_dir, tmp_path):
    from connectra_core.email_sender import log_email
    from connectra_admin.activity_viewer import export_logs_csv

    log_email("user@example.com", "client.com", "Greeting", 2)

    output_path = tmp_path / "activity.csv"
    count = export_logs_csv(output_path)

    content = output_path.read_text(encoding="utf-8")
    assert count == 1
    assert "Time,User,Client,Template,Recipients" in content
    assert "user@example.com,client.com,Greeting,2" in content


def test_release_package_contains_exes_and_manifest(tmp_path):
    from connectra_admin.release_packager import create_release_package

    user_exe = tmp_path / "connectra_user.exe"
    admin_exe = tmp_path / "connectra_admin.exe"
    user_exe.write_bytes(b"user")
    admin_exe.write_bytes(b"admin")

    output_zip = create_release_package(
        tmp_path / "connectra-1.2.3.zip",
        "1.2.3",
        user_exe,
        admin_exe,
    )

    with zipfile.ZipFile(output_zip) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("release_manifest.json"))

    assert {"connectra_user.exe", "connectra_admin.exe", "release_manifest.json"} <= names
    assert manifest["version"] == "1.2.3"


def test_user_bundle_requires_employee_id_for_seeded_package(tmp_path):
    from connectra_admin.user_app_bundle import create_user_app_bundle

    with pytest.raises(ValueError, match="Employee ID"):
        create_user_app_bundle(
            tmp_path / "connectra_user.zip",
            user_email="user@example.com",
            user_passcode="login-pass",
            mailbox_password=None,
            employee_id=None,
        )


def test_user_exe_finder_returns_first_existing_candidate(monkeypatch, tmp_path):
    from connectra_admin import user_app_bundle

    missing_exe = tmp_path / "missing" / "connectra_user.exe"
    existing_exe = tmp_path / "dist" / "connectra_user.exe"
    existing_exe.parent.mkdir()
    existing_exe.write_bytes(b"user exe")

    monkeypatch.setattr(
        user_app_bundle,
        "_candidate_user_exes",
        lambda: [missing_exe, existing_exe],
    )

    assert user_app_bundle.find_existing_user_exe() == existing_exe


def test_backend_summary_and_rollout_api(monkeypatch, tmp_path):
    monkeypatch.setenv("CONNECTRA_RUNTIME_ROOT", str(tmp_path))

    import backend.app as backend_app

    backend_app = importlib.reload(backend_app)

    backend_app.create_email_log(
        backend_app.EmailLog(
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            user_email="user@example.com",
            client_domain="client.com",
            template_name="Greeting",
            recipient_count=3,
        )
    )

    summary = backend_app.report_summary()
    assert summary["emails_sent"] == 1
    assert summary["active_users"] == 1
    assert summary["client_domains"] == 1
    assert summary["templates_used"] == 1
    assert summary["recipients"] == 3

    backend_app.update_rollout_settings(
        backend_app.RolloutSettings(
            available_version="1.2.0",
            approved_version="1.1.0",
            installer_url="https://example.com/connectra.zip",
            release_notes="Approved rollout.",
        )
    )

    rollout = backend_app.get_rollout_settings()
    assert rollout["available_version"] == "1.2.0"
    assert rollout["approved_version"] == "1.1.0"
    assert rollout["installer_url"] == "https://example.com/connectra.zip"
