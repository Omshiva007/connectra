"""Unit tests for connectra_core/validators.py"""

import pytest

from connectra_core.validators import (
    validate_email,
    validate_template,
    validate_contact,
    validate_holiday,
)


# ---------------------------------------------------------------------------
# validate_email
# ---------------------------------------------------------------------------

class TestValidateEmail:

    @pytest.mark.parametrize("addr", [
        "user@example.com",
        "alice.bob@domain.co.uk",
        "user+tag@mail.org",
        "info@company.io",
    ])
    def test_valid_emails(self, addr):
        ok, reason = validate_email(addr)
        assert ok is True
        assert reason == ""

    @pytest.mark.parametrize("addr", [
        "",
        "   ",
        "notanemail",
        "@nodomain.com",
        "noDomain@",
        "double@@at.com",
    ])
    def test_invalid_emails(self, addr):
        ok, reason = validate_email(addr)
        assert ok is False
        assert reason != ""

    def test_none_is_invalid(self):
        ok, _ = validate_email(None)  # type: ignore[arg-type]
        assert ok is False

    def test_non_string_is_invalid(self):
        ok, _ = validate_email(123)  # type: ignore[arg-type]
        assert ok is False


# ---------------------------------------------------------------------------
# validate_template
# ---------------------------------------------------------------------------

class TestValidateTemplate:

    def test_valid_template(self):
        ok, reason = validate_template("Happy New Year", "Wishing you well", "<p>Body</p>")
        assert ok is True

    def test_empty_name_is_invalid(self):
        ok, _ = validate_template("", "Subject", "Body")
        assert ok is False

    def test_whitespace_name_is_invalid(self):
        ok, _ = validate_template("   ", "Subject", "Body")
        assert ok is False

    def test_name_too_long_is_invalid(self):
        ok, _ = validate_template("x" * 256, "Subject", "Body")
        assert ok is False

    def test_empty_subject_is_invalid(self):
        ok, _ = validate_template("Name", "", "Body")
        assert ok is False

    def test_empty_body_is_invalid(self):
        ok, _ = validate_template("Name", "Subject", "")
        assert ok is False

    def test_whitespace_body_is_invalid(self):
        ok, _ = validate_template("Name", "Subject", "   ")
        assert ok is False

    def test_subject_too_long_is_invalid(self):
        ok, _ = validate_template("Name", "S" * 999, "Body")
        assert ok is False

    def test_none_name_is_invalid(self):
        ok, _ = validate_template(None, "Subject", "Body")  # type: ignore[arg-type]
        assert ok is False


# ---------------------------------------------------------------------------
# validate_contact
# ---------------------------------------------------------------------------

class TestValidateContact:

    def test_valid_contact_no_domain(self):
        ok, _ = validate_contact("client@acme.com")
        assert ok is True

    def test_valid_contact_matching_domain(self):
        ok, _ = validate_contact("client@acme.com", domain="acme.com")
        assert ok is True

    def test_domain_mismatch_is_invalid(self):
        ok, reason = validate_contact("client@acme.com", domain="other.com")
        assert ok is False
        assert "acme.com" in reason

    def test_invalid_email_fails_contact_validation(self):
        ok, _ = validate_contact("not-an-email", domain="acme.com")
        assert ok is False

    def test_empty_domain_string_is_invalid(self):
        ok, _ = validate_contact("client@acme.com", domain="")
        assert ok is False

    def test_none_domain_is_allowed(self):
        ok, _ = validate_contact("client@acme.com", domain=None)
        assert ok is True

    def test_domain_case_insensitive(self):
        ok, _ = validate_contact("client@ACME.COM", domain="acme.com")
        assert ok is True


# ---------------------------------------------------------------------------
# validate_holiday
# ---------------------------------------------------------------------------

class TestValidateHoliday:

    def test_valid_holiday_iso_date(self):
        ok, _ = validate_holiday("New Year", "2026-01-01", "New Year Template", 7)
        assert ok is True

    def test_valid_holiday_verbose_date(self):
        ok, _ = validate_holiday("New Year", "January 01, 2026", "Template", 5)
        assert ok is True

    def test_valid_holiday_datetime_format(self):
        ok, _ = validate_holiday("Easter", "2026-04-05 00:00:00", "Template", 3)
        assert ok is True

    def test_empty_holiday_name_is_invalid(self):
        ok, _ = validate_holiday("", "2026-01-01", "Template", 5)
        assert ok is False

    def test_bad_date_format_is_invalid(self):
        ok, reason = validate_holiday("Holiday", "01/01/2026", "Template", 5)
        assert ok is False
        assert "format" in reason.lower() or "recognised" in reason.lower()

    def test_none_date_is_invalid(self):
        ok, _ = validate_holiday("Holiday", None, "Template", 5)  # type: ignore[arg-type]
        assert ok is False

    def test_empty_template_is_invalid(self):
        ok, _ = validate_holiday("Holiday", "2026-01-01", "", 5)
        assert ok is False

    def test_string_reminder_days_converted(self):
        ok, _ = validate_holiday("Holiday", "2026-01-01", "Template", "7")
        assert ok is True

    def test_negative_reminder_days_is_invalid(self):
        ok, _ = validate_holiday("Holiday", "2026-01-01", "Template", -1)
        assert ok is False

    def test_zero_reminder_days_is_valid(self):
        ok, _ = validate_holiday("Holiday", "2026-01-01", "Template", 0)
        assert ok is True

    def test_non_integer_reminder_days_is_invalid(self):
        ok, _ = validate_holiday("Holiday", "2026-01-01", "Template", "abc")
        assert ok is False
