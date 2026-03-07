NOISE_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "icloud.com",
    "proton.me",
    "amazonaws.com",
    "mailchimp.com"
}


def is_noise_domain(domain):
    return domain in NOISE_DOMAINS