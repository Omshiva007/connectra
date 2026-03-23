"""
Tests for connectra_core.validators (email, template, domain validation).
"""
import pytest


# ── Email validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("address", [
    "user@example.com",
    "test.user+tag@domain.co.uk",
    "admin@company.co.uk",
    "user+filter@gmail.com",
])
def test_valid_emails(address, isolated_data_dir):
    from connectra_core.validators import validate_email
    valid, errors = validate_email(address)
    assert valid, f"Expected {address!r} to be valid but got errors: {errors}"


@pytest.mark.parametrize("address", [
    "invalid@",
    "@domain.com",
    "no-domain",
    "",
    "   ",
])
def test_invalid_emails(address, isolated_data_dir):
    from connectra_core.validators import validate_email
    valid, errors = validate_email(address)
    assert not valid, f"Expected {address!r} to be invalid"
    assert errors


# ── Template name validation ──────────────────────────────────────────────────

def test_valid_template_name(isolated_data_dir):
    from connectra_core.validators import validate_template_name
    valid, errors = validate_template_name("Welcome Email")
    assert valid
    assert not errors


def test_template_name_too_long(isolated_data_dir):
    from connectra_core.validators import validate_template_name
    valid, errors = validate_template_name("A" * 101)
    assert not valid
    assert errors


@pytest.mark.parametrize("name", ["Bad<Name>", 'Has"Quotes', "Has'apostrophe"])
def test_template_name_with_invalid_chars(name, isolated_data_dir):
    from connectra_core.validators import validate_template_name
    valid, errors = validate_template_name(name)
    assert not valid
    assert errors


def test_empty_template_name(isolated_data_dir):
    from connectra_core.validators import validate_template_name
    valid, errors = validate_template_name("")
    assert not valid


# ── Full template validation ──────────────────────────────────────────────────

def test_valid_template(isolated_data_dir):
    from connectra_core.validators import validate_template
    valid, errors = validate_template(
        "Welcome Email",
        "Welcome to our service",
        "<h1>Welcome</h1><p>This is a welcome message.</p>",
    )
    assert valid, errors


def test_template_short_body(isolated_data_dir):
    from connectra_core.validators import validate_template
    valid, errors = validate_template("Name", "Subject", "Short")
    assert not valid


def test_template_long_subject(isolated_data_dir):
    from connectra_core.validators import validate_template
    valid, errors = validate_template("Name", "S" * 201, "Valid body text here.")
    assert not valid


# ── Domain validation ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("domain", [
    "example.com",
    "sub.example.co.uk",
    "my-company.io",
])
def test_valid_domains(domain, isolated_data_dir):
    from connectra_core.validators import validate_domain
    valid, errors = validate_domain(domain)
    assert valid, errors


@pytest.mark.parametrize("domain", [
    "",
    "nodot",
    "bad domain.com",
])
def test_invalid_domains(domain, isolated_data_dir):
    from connectra_core.validators import validate_domain
    valid, errors = validate_domain(domain)
    assert not valid
