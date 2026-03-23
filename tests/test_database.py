"""Unit tests for connectra_core/database.py"""

import sqlite3
from unittest.mock import patch

import pytest

import connectra_core.database as db_mod
from connectra_core.database import initialize_database


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
    """Tests for get_connection()."""

    def test_returns_sqlite_connection(self, user_db_conn):
        conn = db_mod.get_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_creates_clients_table(self, user_db_conn):
        conn = db_mod.get_connection()
        assert "clients" in _table_names(conn)
        conn.close()

    def test_creates_contacts_table(self, user_db_conn):
        conn = db_mod.get_connection()
        assert "contacts" in _table_names(conn)
        conn.close()

    def test_creates_email_logs_table(self, user_db_conn):
        conn = db_mod.get_connection()
        assert "email_logs" in _table_names(conn)
        conn.close()

    def test_clients_domain_unique_constraint(self, user_db_conn):
        conn = db_mod.get_connection()
        conn.execute("INSERT INTO clients(domain) VALUES('acme.com')")
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO clients(domain) VALUES('acme.com')")
        conn.close()

    def test_contacts_email_unique_constraint(self, user_db_conn):
        conn = db_mod.get_connection()
        conn.execute("INSERT INTO contacts(email, domain) VALUES('a@acme.com', 'acme.com')")
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO contacts(email, domain) VALUES('a@acme.com', 'acme.com')")
        conn.close()

    def test_insert_and_retrieve_email_log(self, user_db_conn):
        conn = db_mod.get_connection()
        conn.execute(
            "INSERT INTO email_logs(timestamp, user_email, client_domain, template_name, recipient_count)"
            " VALUES(?,?,?,?,?)",
            ("2026-01-01T10:00:00", "me@company.com", "acme.com", "New Year", 5),
        )
        conn.commit()
        conn.close()

        row = user_db_conn.execute("SELECT * FROM email_logs").fetchone()
        assert row is not None
        assert row[2] == "me@company.com"
        assert row[5] == 5


class TestInitializeDatabase:
    """Tests for initialize_database()."""

    def test_initialize_does_not_raise(self, user_db_conn):
        # Should run without errors
        initialize_database()

    def test_initialize_is_idempotent(self, user_db_conn):
        initialize_database()
        initialize_database()  # second call should not fail
        conn = db_mod.get_connection()
        assert "clients" in _table_names(conn)
        conn.close()


class TestPlatformIndependentPath:
    """Ensure the database module does NOT hard-code C:/Connectra."""

    def test_db_path_not_hardcoded_windows(self):
        import inspect
        source = inspect.getsource(db_mod)
        assert "C:/Connectra" not in source, (
            "connectra_core/database.py still contains a hardcoded Windows path"
        )
