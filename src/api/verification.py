from datetime import datetime, timezone
from config import SECRET, SITE_URL

import jwt

def generate_jwt(discord_id: str):
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
    jwt_token = generate_jwt(discord_id)
    url = f"{SITE_URL}/verify?token=" + jwt_token

    return url
