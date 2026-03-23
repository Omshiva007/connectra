"""Unit tests for connectra_core/holiday_checker.py"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from connectra_core.holiday_checker import check_upcoming_holidays


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_holiday(conn, holiday, date_str, template, reminder_days, active=1):
    conn.execute(
        "INSERT INTO holiday_calendar(holiday, date, template, reminder_days, active)"
        " VALUES(?,?,?,?,?)",
        (holiday, date_str, template, reminder_days, active),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckUpcomingHolidays:

    def test_returns_empty_when_no_holidays(self, admin_db_conn):
        result = check_upcoming_holidays()
        assert result == []

    def test_returns_holiday_on_reminder_date(self, admin_db_conn):
        today = date.today()
        reminder_days = 3
        holiday_date = today + timedelta(days=reminder_days)

        _insert_holiday(
            admin_db_conn,
            "Test Holiday",
            holiday_date.strftime("%Y-%m-%d"),
            "Greet Template",
            reminder_days,
        )

        result = check_upcoming_holidays()
        assert len(result) == 1
        assert result[0]["holiday"] == "Test Holiday"
        assert result[0]["template"] == "Greet Template"
        assert result[0]["date"] == holiday_date

    def test_ignores_holiday_not_yet_due(self, admin_db_conn):
        today = date.today()
        reminder_days = 5
        holiday_date = today + timedelta(days=reminder_days + 10)  # too far away

        _insert_holiday(
            admin_db_conn,
            "Future Holiday",
            holiday_date.strftime("%Y-%m-%d"),
            "Future Template",
            reminder_days,
        )

        result = check_upcoming_holidays()
        assert result == []

    def test_ignores_inactive_holiday(self, admin_db_conn):
        today = date.today()
        reminder_days = 2
        holiday_date = today + timedelta(days=reminder_days)

        _insert_holiday(
            admin_db_conn,
            "Inactive Holiday",
            holiday_date.strftime("%Y-%m-%d"),
            "Some Template",
            reminder_days,
            active=0,
        )

        result = check_upcoming_holidays()
        assert result == []

    def test_parses_verbose_date_format(self, admin_db_conn):
        today = date.today()
        reminder_days = 1
        holiday_date = today + timedelta(days=reminder_days)
        verbose_date = holiday_date.strftime("%B %d, %Y")

        _insert_holiday(
            admin_db_conn,
            "Verbose Date Holiday",
            verbose_date,
            "Template",
            reminder_days,
        )

        result = check_upcoming_holidays()
        assert len(result) == 1
        assert result[0]["holiday"] == "Verbose Date Holiday"

    def test_skips_holiday_with_bad_date(self, admin_db_conn):
        _insert_holiday(
            admin_db_conn,
            "Bad Date Holiday",
            "not-a-date",
            "Template",
            0,
        )
        # Should not raise; bad row is skipped
        result = check_upcoming_holidays()
        assert result == []

    def test_skips_holiday_with_null_date(self, admin_db_conn):
        admin_db_conn.execute(
            "INSERT INTO holiday_calendar(holiday, date, template, reminder_days, active)"
            " VALUES(?,?,?,?,?)",
            ("Null Date", None, "Template", 0, 1),
        )
        admin_db_conn.commit()

        result = check_upcoming_holidays()
        assert result == []

    def test_multiple_holidays_same_day(self, admin_db_conn):
        today = date.today()
        for i, name in enumerate(["Holiday A", "Holiday B"]):
            reminder_days = i + 1
            holiday_date = today + timedelta(days=reminder_days)
            _insert_holiday(
                admin_db_conn,
                name,
                holiday_date.strftime("%Y-%m-%d"),
                f"Template {i}",
                reminder_days,
            )

        result = check_upcoming_holidays()
        names = {r["holiday"] for r in result}
        assert "Holiday A" in names
        assert "Holiday B" in names

    def test_holiday_checker_not_hardcoded_path(self):
        import connectra_core.holiday_checker as mod
        import inspect
        source = inspect.getsource(mod)
        assert "C:/Connectra" not in source, (
            "connectra_core/holiday_checker.py still contains a hardcoded Windows path"
        )
        assert r"C:\Connectra" not in source, (
            "connectra_core/holiday_checker.py still contains a hardcoded Windows path"
        )

    def test_connectra_home_env_var_sets_admin_db_path(self, tmp_path, monkeypatch):
        """CONNECTRA_HOME env var must control where the admin DB is created."""
        import importlib
        custom_home = str(tmp_path / "custom_home")
        monkeypatch.setenv("CONNECTRA_HOME", custom_home)

        import connectra_core.holiday_checker as mod
        importlib.reload(mod)

        from pathlib import Path
        expected = Path(custom_home) / "data" / "connectra_admin.db"
        assert mod.ADMIN_DB == expected
