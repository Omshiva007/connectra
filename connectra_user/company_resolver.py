"""Simple domain-to-company display-name helper."""


def domain_to_company(domain):
    """Convert a domain such as example.com into Example."""

    name = domain.split(".")[0]

    return name.capitalize()
