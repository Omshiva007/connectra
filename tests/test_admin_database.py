"""Unit tests for connectra_core/admin_database.py"""

import sqlite3
from unittest.mock import patch

import pytest

import connectra_core.admin_database as admin_db_mod
from connectra_core.admin_database import get_setting, set_setting


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_names(conn: sqlite3.Connection) -> set:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetConnection:
    def test_returns_connection(self, admin_db_conn):
        conn = admin_db_mod.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_users_table_exists(self, admin_db_conn):
        conn = admin_db_mod.get_connection()
        assert "users" in _table_names(conn)
        conn.close()

    def test_settings_table_exists(self, admin_db_conn):
        conn = admin_db_mod.get_connection()
        assert "settings" in _table_names(conn)
        conn.close()

    def test_users_email_unique(self, admin_db_conn):
        conn = admin_db_mod.get_connection()
        conn.execute("INSERT INTO users(email, app_password) VALUES('a@b.com', 'pass')")
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO users(email, app_password) VALUES('a@b.com', 'other')")
        conn.close()

    def test_insert_user(self, admin_db_conn):
        conn = admin_db_mod.get_connection()
        conn.execute(
            "INSERT INTO users(email, app_password, active) VALUES(?,?,?)",
            ("admin@company.com", "secret", 1),
        )
        conn.commit()
        conn.close()

        row = admin_db_conn.execute("SELECT email FROM users").fetchone()
        assert row[0] == "admin@company.com"


class TestGetSetting:
    def test_returns_none_for_missing_key(self, admin_db_conn):
        result = get_setting("nonexistent_key")
        assert result is None

    def test_returns_value_after_set(self, admin_db_conn):
        set_setting("logo_path", "/path/to/logo.png")
        result = get_setting("logo_path")
        assert result == "/path/to/logo.png"


class TestSetSetting:
    def test_insert_new_setting(self, admin_db_conn):
        set_setting("theme", "dark")
        assert get_setting("theme") == "dark"

    def test_update_existing_setting(self, admin_db_conn):
        set_setting("theme", "dark")
        set_setting("theme", "light")
        assert get_setting("theme") == "light"

    def test_multiple_settings_independent(self, admin_db_conn):
        set_setting("key1", "value1")
        set_setting("key2", "value2")
        assert get_setting("key1") == "value1"
        assert get_setting("key2") == "value2"


class TestPlatformIndependentPath:
    def test_admin_db_path_not_hardcoded(self):
        import inspect
        source = inspect.getsource(admin_db_mod)
        assert "C:/Connectra" not in source, (
            "connectra_core/admin_database.py still contains a hardcoded Windows path"
        )
