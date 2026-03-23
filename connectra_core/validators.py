"""
Input validation helpers used throughout Connectra.

All functions return a ``(is_valid: bool, errors: list[str])`` tuple so callers
can decide whether to surface the error messages to the user or raise an
exception.
"""
import re
from typing import Tuple

_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

_NO_HTML_CHARS_RE = re.compile(r"^[^<>\"']+$")


def validate_email(email: str) -> Tuple[bool, list]:
    """Return ``(True, [])`` when *email* looks like a valid address."""
    errors: list = []
    if not email or not email.strip():
        errors.append("Email address must not be empty.")
    elif not _EMAIL_RE.match(email.strip()):
        errors.append(f"'{email}' is not a valid email address.")
    return len(errors) == 0, errors


def validate_template_name(name: str) -> Tuple[bool, list]:
    """Return ``(True, [])`` when *name* is a safe, non-empty template name."""
    errors: list = []
    if not name or not name.strip():
        errors.append("Template name must not be empty.")
    elif len(name) > 100:
        errors.append("Template name must be 100 characters or fewer.")
    elif not _NO_HTML_CHARS_RE.match(name):
        errors.append("Template name contains invalid characters (< > \" ').")
    return len(errors) == 0, errors


def validate_template(
    name: str, subject: str, body: str
) -> Tuple[bool, list]:
    """Validate all three fields of an email template."""
    errors: list = []

    name_ok, name_errors = validate_template_name(name)
    errors.extend(name_errors)

    if not subject or not subject.strip():
        errors.append("Subject must not be empty.")
    elif len(subject) > 200:
        errors.append("Subject must be 200 characters or fewer.")

    if not body or not body.strip():
        errors.append("Body must not be empty.")
    elif len(body.strip()) < 10:
        errors.append("Body must be at least 10 characters long.")

    return len(errors) == 0, errors


def validate_domain(domain: str) -> Tuple[bool, list]:
    """Return ``(True, [])`` when *domain* looks like a valid hostname."""
    errors: list = []
    pattern = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )
    if not domain or not domain.strip():
        errors.append("Domain must not be empty.")
    elif not pattern.match(domain.strip()):
        errors.append(f"'{domain}' is not a valid domain name.")
    return len(errors) == 0, errors
