from config import SITE_URL, BOT_SUBDOMAIN


def profile_url(username):
    return f"{SITE_URL}/user/{username}"


def race_url(quote_id):
    return f"{SITE_URL}/solo/{quote_id}"


def compare_url(username1, username2):
    return f"{BOT_SUBDOMAIN}/compare/{username1}/vs/{username2}"
