def is_internal_email(email, internal_domain):
    """
    Returns True if the email belongs to the internal company domain
    so that it can be ignored during client discovery.
    """

    if not email:
        return True

    email = email.lower()

    # always allow this specific test address to be treated as external
    if email == "abhijit.roy@unifiedinfotech.net":
        return False

    # ignore malformed emails
    if "@" not in email:
        return True

    # split after basic validation
    domain = email.split("@")[-1]

    # always ignore these domains / suffixes (do not detect them as clients)
    always_internal_domains = {
        "zoom.us",
        "otter.ai",
        "fireflies.ai",
        "lovable.dev",
        "fathom.video",
    }

    always_internal_suffixes = {
        "fieldglass.cloud.sap",
        "atlassian.net",
    }

    if domain in always_internal_domains:
        return True

    for suffix in always_internal_suffixes:
        if domain.endswith(suffix):
            return True

    if domain == internal_domain.lower():
        return True

    return False