"""Mailbox provider settings shared by scanner and sender.

Admins can override these values in the Admin app. Gmail remains the default so
the prototype keeps working until a customer-specific provider is configured.
"""

from dataclasses import dataclass

from connectra_core.admin_database import get_setting

PROVIDER_PRESETS = {
    "gmail": {
        "imap_server": "imap.gmail.com",
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
    },
    "microsoft365": {
        "imap_server": "outlook.office365.com",
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_tls": True,
    },
    "zoho": {
        "imap_server": "imap.zoho.com",
        "smtp_server": "smtp.zoho.com",
        "smtp_port": 587,
        "use_tls": True,
    },
}


@dataclass(frozen=True)
class MailSettings:
    """Resolved mailbox connection settings used at runtime."""

    provider: str = "gmail"
    imap_server: str = "imap.gmail.com"
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True


def _get_bool_setting(key: str, default: bool) -> bool:
    """Read a boolean setting using common admin-entered truthy values."""
    value = get_setting(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_setting(key: str, default: int) -> int:
    """Read an integer setting, falling back when admin input is invalid."""
    value = get_setting(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_provider_preset(provider: str) -> dict:
    """Return known provider defaults, falling back to Gmail."""
    return PROVIDER_PRESETS.get((provider or "gmail").strip().lower(), PROVIDER_PRESETS["gmail"])


def get_mail_settings() -> MailSettings:
    """Return mailbox settings from admin configuration with safe defaults."""
    provider = (get_setting("mail_provider") or MailSettings.provider).strip().lower()
    preset = get_provider_preset(provider)

    return MailSettings(
        provider=provider,
        imap_server=get_setting("imap_server") or preset["imap_server"],
        smtp_server=get_setting("smtp_server") or preset["smtp_server"],
        smtp_port=_get_int_setting("smtp_port", preset["smtp_port"]),
        use_tls=_get_bool_setting("smtp_use_tls", preset["use_tls"]),
    )
