"""Tests for shared admin database helpers used by both desktop apps."""


def test_admin_account_verification_is_separate_from_users(isolated_data_dir):
    from connectra_admin.database_admin import (
        add_admin_account,
        add_user,
        get_admin_accounts,
        verify_admin_login,
    )

    add_user("EMP001", "user@example.com", "user-login")
    add_admin_account("admin@example.com", "admin-password")

    assert get_admin_accounts() == [("admin@example.com", 1)]
    assert verify_admin_login("admin@example.com", "admin-password")
    assert not verify_admin_login("user@example.com", "user-login")
    assert not verify_admin_login("admin@example.com", "mailbox-api-key")


def test_add_user_encrypts_password(isolated_data_dir):
    from connectra_core.admin_database import add_user, get_connection

    add_user("EMP001", "admin@example.com", "secret-pass")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT login_passcode FROM users WHERE email=?", ("admin@example.com",))
    stored_password = cursor.fetchone()[0]
    conn.close()

    assert stored_password != "secret-pass"


def test_get_user_login_and_employee_id_decrypts_correctly(isolated_data_dir):
    from connectra_core.admin_database import (
        add_user,
        get_user_employee_id,
        get_user_login_passcode,
    )

    add_user("EMP001", "admin@example.com", "login-pass")

    assert get_user_employee_id("admin@example.com") == "EMP001"
    assert get_user_login_passcode("admin@example.com") == "login-pass"


def test_update_user_changes_employee_id_email_and_login(isolated_data_dir):
    from connectra_core.admin_database import (
        add_user,
        get_user_employee_id,
        get_user_login_passcode,
        update_user,
        user_exists,
    )

    add_user("EMPOLD", "old@example.com", "old-login")

    updated_count = update_user(
        "old@example.com",
        "EMPNEW",
        "new@example.com",
        "new-login",
    )

    assert updated_count == 1
    assert not user_exists("old@example.com")
    assert user_exists("new@example.com")
    assert get_user_employee_id("new@example.com") == "EMPNEW"
    assert get_user_login_passcode("new@example.com") == "new-login"


def test_user_exists_reports_configured_users(isolated_data_dir):
    from connectra_core.admin_database import add_user, user_exists

    add_user("EMP001", "admin@example.com", "secret-pass")

    assert user_exists("admin@example.com")
    assert not user_exists("missing@example.com")


def test_get_all_users_does_not_return_passwords(isolated_data_dir):
    from connectra_core.admin_database import add_user, get_all_users

    add_user("EMP001", "admin@example.com", "secret-pass")

    assert get_all_users() == [("EMP001", "admin@example.com", 1)]


def test_delete_user_removes_saved_identity(isolated_data_dir):
    from connectra_core.admin_database import (
        add_user,
        delete_user,
        get_user_login_passcode,
        user_exists,
    )

    add_user("EMP001", "admin@example.com", "secret-pass")

    deleted_count = delete_user("admin@example.com")

    assert deleted_count == 1
    assert not user_exists("admin@example.com")
    assert get_user_login_passcode("admin@example.com") is None


def test_settings_round_trip(isolated_data_dir):
    from connectra_core.admin_database import get_setting, set_setting

    set_setting("approved_version", "1.2.3")

    assert get_setting("approved_version") == "1.2.3"
    assert get_setting("missing") is None
