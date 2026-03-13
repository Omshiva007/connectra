def is_internal_email(email, internal_domain):
    """
    Returns True if the email belongs to the internal company domain
    so that it can be ignored during client discovery.
    """

    if not email:
        return True

    email = email.lower()

    # ignore malformed emails
    if "@" not in email:
        return True

    domain = email.split("@")[-1]

    if domain == internal_domain.lower():
        return True

    return False