"""Discord users in users.db: linkage, themes and settings."""

import json
import sqlite3

from config import DEFAULT_UNIVERSE, FORCE_NO_GG_PLUS
from database.bot import db
from utils import dates
from utils.colors import DEFAULT_THEME
from utils.schemas import Theme


def add_user(discord_id: str) -> dict:
    """Insert a new Discord user with default settings and return them."""
    user = {
        "discordId": discord_id,
        "userId": None,
        "theme": json.dumps(DEFAULT_THEME),
        # Frozen pre-command_log archive. Nothing writes it after this insert.
        "commands": json.dumps({
            "counts": {},
            "server": 0,
            "dm": 0,
        }),
        "joined": dates.now().timestamp(),
        "startDate": None,
        "endDate": None,
        "isBanned": 0,
        "isAdmin": 0,
        "isPrivacyWarned": 0,
        "isGgPlus": 0,
        "timezone": "UTC",
        "universe": DEFAULT_UNIVERSE,
    }
    user_values = user.values()

    db.run(f"INSERT INTO users VALUES ({",".join(["?"] * len(user_values))})", list(user_values))

    return user


def get_user(discord_id: str, auto_insert: bool = True) -> dict | None:
    """Returns a user object given a Discord ID. Optionally create a new user if no record is found."""
    results = db.fetch("""
        SELECT * FROM users
        WHERE discordId = ?
        LIMIT 1
    """, [discord_id])

    if results:
        user = results[0]
    elif auto_insert:
        user = add_user(discord_id)
    else:
        return None

    user = dict(user)
    user["theme"] = json.loads(user["theme"])
    if user["discordId"] in FORCE_NO_GG_PLUS:
        user["isGgPlus"] = 0
    return user


def get_user_by_user_id(user_id: str) -> dict | None:
    """Returns a user object given a TypeGG user ID."""
    results = db.fetch("""
        SELECT * FROM users
        WHERE userId = ?
        LIMIT 1
    """, [user_id])

    if results:
        user = results[0]
    else:
        return None

    user = dict(user)
    user["theme"] = json.loads(user["theme"])
    if user["discordId"] in FORCE_NO_GG_PLUS:
        user["isGgPlus"] = 0
    return user


def get_user_ids() -> list[int]:
    """Return every registered Discord ID."""
    users = db.fetch("SELECT discordId FROM users")

    return [int(user[0]) for user in users]


def get_theme(discord_id: int) -> Theme | None:
    """Returns a user's theme if they exist."""
    results = db.fetch("SELECT theme FROM users WHERE discordId = ?", [discord_id])

    return json.loads(results[0]["theme"]) if results else None


def update_theme(discord_id: str, theme: Theme) -> None:
    """Replace a user's saved theme."""
    db.run("""
        UPDATE users
        SET theme = ?
        WHERE discordId = ?
    """, [json.dumps(theme), discord_id])


def update_warning(discord_id: str) -> None:
    """Record that a user has seen the privacy warning."""
    db.run("""
        UPDATE users
        SET isPrivacyWarned = 1
        WHERE discordId = ?
    """, [discord_id])


def update_gg_plus_status(user_id: str, is_gg_plus: bool) -> None:
    """Update a user's GG+ subscription status."""
    if get_discord_id(user_id) in FORCE_NO_GG_PLUS:
        return

    db.run("""
        UPDATE users
        SET isGgPlus = ?
        WHERE userId = ?
    """, [1 if is_gg_plus else 0, user_id])


def update_timezone(discord_id: str, timezone: str) -> None:
    """Update a user's timezone."""
    db.run("""
        UPDATE users
        SET timezone = ?
        WHERE discordId = ?
    """, [timezone, discord_id])


def update_universe(discord_id: str, universe: str) -> None:
    """Update the universe a user's commands run in."""
    db.run("""
        UPDATE users
        SET universe = ?
        WHERE discordId = ?
    """, [universe, discord_id])


def update_date_range(discord_id: str, start: float | None, end: float | None) -> None:
    """Store a user's time travel range as Unix seconds, or clear it with a pair of Nones."""
    db.run("""
        UPDATE users
        SET startDate = ?, endDate = ?
        WHERE discordId = ?
    """, [start, end, discord_id])


def link_user(discord_id: str, user_id: str) -> None:
    """Creates a link between a Discord ID and a User ID."""
    db.run("""
        UPDATE users
        SET userId = ?
        WHERE discordId = ?
    """, [user_id, discord_id])


def unlink_user(discord_id: str) -> None:
    """Removes the link between a Discord ID and a User ID."""
    db.run("""
        UPDATE users
        SET userId = NULL
        WHERE discordId = ?
    """, [discord_id])


def get_all_linked_users() -> dict[str, str]:
    """Returns a dictionary of user IDs and Discord ID."""
    results = db.fetch("""
        SELECT discordId, userId
        FROM users
        WHERE userId IS NOT NULL
    """)

    return {str(row["userId"]): str(row["discordId"]) for row in results}


def ban_user(discord_id: str) -> None:
    """Ban a user from using the bot."""
    db.run("""
        UPDATE users
        SET isBanned = 1
        WHERE discordId = ?
    """, [discord_id])


def unban_user(discord_id: str) -> None:
    """Lift a user's ban."""
    db.run("""
        UPDATE users
        SET isBanned = 0
        WHERE discordId = ?
    """, [discord_id])


def admin_user(discord_id: str) -> None:
    """Grant a user admin privileges."""
    db.run("""
        UPDATE users
        SET isAdmin = 1
        WHERE discordId = ?
    """, [discord_id])


def unadmin_user(discord_id: str) -> None:
    """Revoke a user's admin privileges."""
    db.run("""
        UPDATE users
        SET isAdmin = 0
        WHERE discordId = ?
    """, [discord_id])


def get_admin_users() -> list[sqlite3.Row]:
    """Return the Discord IDs of every admin."""
    results = db.fetch("""
        SELECT discordId FROM users
        WHERE isAdmin = 1
    """)

    return results


def get_discord_id(user_id: str) -> str | None:
    """Return the Discord ID linked to a TypeGG user ID, if any."""
    result = db.fetch_one("SELECT discordId FROM users WHERE userId = ?", [user_id])
    if not result:
        return None

    return result["discordId"]
