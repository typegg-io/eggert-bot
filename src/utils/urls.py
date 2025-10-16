from config import SITE_URL


def profile_url(username):
    return f"{SITE_URL}/user/{username}"


def race_url(text_id):
    return f"{SITE_URL}/solo/{text_id}"
