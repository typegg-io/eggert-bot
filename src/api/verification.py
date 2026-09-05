"""Signed links that verify a Discord account against the site."""

from datetime import UTC, datetime

import jwt

from config import BOT_SUBDOMAIN, SECRET, SITE_URL


def generate_jwt(discord_id: str) -> str:
    """Generates a JWT containing a Discord ID. Expires after 10 minutes."""
    issued_at = int(datetime.now(UTC).timestamp())
    expiration = issued_at + 600
    payload = {
        "discordId": discord_id,
        "iat": issued_at,
        "exp": expiration,
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return token


def generate_link(discord_id: str) -> str:
    """Creates a verification URL containing a signed JWT for the user."""
    jwt_token = generate_jwt(discord_id)
    return f"{SITE_URL}/verify?token=" + jwt_token


# The verification token above carries a discordId too, so both kinds name their scope.
DASHBOARD_SCOPE = "dashboard-link"
DASHBOARD_MINUTES = 10


def generate_dashboard_link(discord_id: str) -> str:
    """Creates a single-use dashboard URL containing a signed JWT for an admin."""
    expiration = int(datetime.now(UTC).timestamp()) + DASHBOARD_MINUTES * 60
    payload = {
        "discordId": discord_id,
        "scope": DASHBOARD_SCOPE,
        "exp": expiration,
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return f"{BOT_SUBDOMAIN}/dashboard?token=" + token
