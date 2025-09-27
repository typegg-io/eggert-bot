from config import SITE_URL


def profile(username):
    return f"{SITE_URL}/user/{username}"


def race(text_id):
    return f"{SITE_URL}/solo/{text_id}"
