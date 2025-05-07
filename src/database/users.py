import json
from config import default_theme
from database import db

def create_table():
    db.run(f"""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            theme JSON NOT NULL,
            user_id TEXT
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

    if results:
        user = results[0]
    else:
        user = add_user(discord_id)

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

def get_all_linked_users():
    """
    Return all Discord ID and user ID pairs for linked users.
    Returns a list of tuples (discord_id, user_id).
    """
    results = db.fetch("""
        SELECT discord_id, user_id
        FROM users
        WHERE user_id IS NOT NULL
    """)

    return [(str(row['discord_id']), str(row['user_id'])) for row in results]

def is_user_linked(discord_id: str) -> bool:
    """
    Check if a Discord user is linked to a user ID.
    """
    results = db.fetch("""
        SELECT user_id
        FROM users
        WHERE discord_id = ? AND user_id IS NOT NULL
    """, [discord_id])

    return len(results) > 0
