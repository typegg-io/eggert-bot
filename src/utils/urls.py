"""Links to the site, and the parser that reads one back."""

import re
from urllib.parse import urlparse

from config import BOT_SUBDOMAIN, SITE_URL

GG_PLUS_LINK = f"{SITE_URL}/plus"

_SITE_HOST = urlparse(SITE_URL or "").netloc
_SOLO_URL_RE = re.compile(
    rf"^https?://(?:[a-z0-9-]+\.)?{re.escape(_SITE_HOST)}/solo/(?P<quote_id>[^/?#]+)",
    re.IGNORECASE,
)


def parse_solo_url(arg: str) -> str | None:
    """Extract the quote ID from a solo link on the base site or universe subdomain."""
    match = _SOLO_URL_RE.match(arg)
    return match.group("quote_id") if match else None


def profile_url(username) -> str:
    """Return the link to a user's profile."""
    return f"{SITE_URL}/user/{username}"


def race_url(quote_id) -> str:
    """Return the link to a quote's solo page."""
    return f"{SITE_URL}/solo/{quote_id}"


def compare_url(username1, username2) -> str:
    """Return the link to the bot's compare page for two users."""
    return f"{BOT_SUBDOMAIN}/compare/{username1}/vs/{username2}"
