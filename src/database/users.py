import json

from config import default_theme
from database import db


def create_table():
    db.run(f"""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            theme TEXT NOT NULL, -- JSON String
            user_id TEXT DEFAULT NULL
        )
    """)


def add_user(discord_id: str):
    user = {
        "discord_id": discord_id,
        "theme": json.dumps(default_theme),
        "user_id": None,
    }

    db.run("""
        INSERT INTO users VALUES (?, ?, ?)
    """, [discord_id, user["theme"], None])

    return user


def get_user(discord_id: str):
    results = db.fetch("""
        SELECT * FROM users
        WHERE discord_id = ?
        LIMIT 1
    """, [discord_id])

    if not results:
        user = add_user(discord_id)
    else:
        user = results[0]

    user = dict(user)
    user["theme"] = json.loads(user["theme"])
    return user


def update_theme(discord_id: str, theme: dict):
    db.run("""
        UPDATE users
        SET theme = ?
        WHERE discord_id = ?
    """, [json.dumps(theme), discord_id])


def link_user(discord_id: str, user_id: str):
    db.run("""
        UPDATE users
        SET user_id = ?
        WHERE discord_id = ?
    """, [user_id, discord_id])


def unlink_user(discord_id: str):
    db.run("""
        UPDATE users
        SET user_id = NULL
        WHERE discord_id = ?
    """, [discord_id])
