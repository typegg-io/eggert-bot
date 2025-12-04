from datetime import datetime, timezone

import jwt

from config import SECRET, SITE_URL


def generate_jwt(discord_id: str):
    """Generates a JWT containing a Discord ID. Expires after 10 minutes."""
    issued_at = int(datetime.now(timezone.utc).timestamp())
    expiration = issued_at + 600
    payload = {
        "discordId": discord_id,
        "iat": issued_at,
        "exp": expiration,
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return token


def generate_link(discord_id: str):
    """Creates a verification URL containing a signed JWT for the user."""
    jwt_token = generate_jwt(discord_id)
    return f"{SITE_URL}/verify?token=" + jwt_token
