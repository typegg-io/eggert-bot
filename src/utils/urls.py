import re
from urllib.parse import urlparse

from config import SITE_URL, BOT_SUBDOMAIN

_SITE_HOST = urlparse(SITE_URL or "").netloc
_SOLO_URL_RE = re.compile(
    rf"^https?://(?:[a-z0-9-]+\.)?{re.escape(_SITE_HOST)}/solo/(?P<quote_id>[^/?#]+)",
    re.IGNORECASE,
)


def parse_solo_url(arg: str):
    """Extract the quote ID from a solo link on the base site or universe subdomain."""
    match = _SOLO_URL_RE.match(arg)
    return match.group("quote_id") if match else None


def profile_url(username):
    return f"{SITE_URL}/user/{username}"


def race_url(quote_id):
    return f"{SITE_URL}/solo/{quote_id}"


def compare_url(username1, username2):
    return f"{BOT_SUBDOMAIN}/compare/{username1}/vs/{username2}"
