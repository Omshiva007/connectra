"""Input validation helpers for Connectra."""

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> tuple[bool, str]:
    """Validate an email address format.

    Returns (True, "") on success, (False, reason) on failure.
    """
    if not email or not isinstance(email, str):
        return False, "Email must be a non-empty string"

    email = email.strip()

    if not _EMAIL_RE.match(email):
        return False, f"Invalid email format: {email!r}"

    return True, ""


def validate_template(name: str, subject: str, body: str) -> tuple[bool, str]:
    """Validate an email template.

    Returns (True, "") on success, (False, reason) on failure.
    """
    if not name or not isinstance(name, str) or not name.strip():
        return False, "Template name must be a non-empty string"

    if len(name.strip()) > 255:
        return False, "Template name must not exceed 255 characters"

    if not subject or not isinstance(subject, str) or not subject.strip():
        return False, "Template subject must be a non-empty string"

    if len(subject.strip()) > 998:
        return False, "Template subject must not exceed 998 characters (RFC 5322)"

    if not body or not isinstance(body, str) or not body.strip():
        return False, "Template body must be a non-empty string"

    return True, ""


def validate_contact(email: str, domain: str | None = None) -> tuple[bool, str]:
    """Validate a contact entry.

    Returns (True, "") on success, (False, reason) on failure.
    """
    ok, reason = validate_email(email)
    if not ok:
        return False, reason

    if domain is not None:
        if not isinstance(domain, str) or not domain.strip():
            return False, "Domain must be a non-empty string when provided"

        email_domain = email.strip().lower().split("@")[-1]
        if email_domain != domain.strip().lower():
            return False, (
                f"Contact email domain {email_domain!r} does not match "
                f"expected domain {domain!r}"
            )

    return True, ""


def validate_holiday(
    holiday: str,
    date_str: str,
    template: str,
    reminder_days: int | str,
) -> tuple[bool, str]:
    """Validate a holiday calendar entry.

    Returns (True, "") on success, (False, reason) on failure.
    """
    from datetime import datetime

    if not holiday or not isinstance(holiday, str) or not holiday.strip():
        return False, "Holiday name must be a non-empty string"

    if not date_str or not isinstance(date_str, str):
        return False, "Holiday date must be a non-empty string"

    parsed = None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return False, (
            f"Holiday date {date_str!r} is not in a recognised format "
            "(expected YYYY-MM-DD or 'Month DD, YYYY')"
        )

    if not template or not isinstance(template, str) or not template.strip():
        return False, "Holiday template must be a non-empty string"

    try:
        days = int(reminder_days)
    except (TypeError, ValueError):
        return False, f"Reminder days must be an integer, got {reminder_days!r}"

    if days < 0:
        return False, "Reminder days must be a non-negative integer"

    return True, ""
