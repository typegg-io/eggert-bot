from datetime import datetime, timezone

import jwt

base_url = "https://api.typegg.io"
from config import secret

access_token = "placeholder"


def generate_jwt(discord_id: str):
    issued_at = int(datetime.now(timezone.utc).timestamp())
    expiration = issued_at + 600
    payload = {
        "discordId": discord_id,
        "userId": "keegan",
        "iat": issued_at,
        "exp": expiration,
    }
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


def generate_link(discord_id: str):
    jwt_token = generate_jwt(discord_id)
    url = "https://typegg.io/verify?token=" + jwt_token

    return url
