"""Discord users in users.db: linkage, themes, settings and the command log."""

import json
import sqlite3

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
    return user


def get_user_ids() -> list[int]:
    """Return every registered Discord ID."""
    users = db.fetch("SELECT discordId FROM users")

    return [int(user[0]) for user in users]


def get_command_usage(discord_id: int | str) -> dict[str, int]:
    """Return command counts for a single user."""
    results = db.fetch("""
        SELECT command, COUNT(*) AS total FROM command_log
        WHERE discordId = ?
        GROUP BY command
    """, [str(discord_id)])

    return {row["command"]: row["total"] for row in results}


def get_all_command_usage() -> dict[str, int]:
    """Return total command counts across all users."""
    results = db.fetch("""
        SELECT command, COUNT(*) AS total FROM command_log
        GROUP BY command
    """)

    return {row["command"]: row["total"] for row in results}


def get_command_leaderboard(command_name: str) -> list[dict]:
    """Return every user who has run a command, most usages first."""
    results = db.fetch("""
        SELECT discordId, COUNT(*) AS total FROM command_log
        WHERE command = ?
        GROUP BY discordId
        ORDER BY total DESC
    """, [command_name])

    return [{"discord_id": row["discordId"], "usages": row["total"]} for row in results]


def get_top_users_by_command_usage() -> list[dict]:
    """Return users sorted by total command usage."""
    results = db.fetch("""
        SELECT discordId, COUNT(*) AS total FROM command_log
        GROUP BY discordId
        ORDER BY total DESC
    """)

    return [{"discord_id": row["discordId"], "total_commands": row["total"]} for row in results]


def get_theme(discord_id: int) -> Theme | None:
    """Returns a user's theme if they exist."""
    results = db.fetch("SELECT theme FROM users WHERE discordId = ?", [discord_id])

    return json.loads(results[0]["theme"]) if results else None


def log_command(discord_id: str, user_id: str | None, command_name: str, origin: str) -> None:
    """Record one command invocation."""
    db.run("""
        INSERT INTO command_log (discordId, userId, command, origin, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, [str(discord_id), user_id, command_name, origin, dates.now().timestamp()])


def get_command_count() -> int:
    """Return the total number of commands ever run."""
    return db.fetch_one("SELECT COUNT(*) AS total FROM command_log")["total"]


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


def migrate_command_name(old_name: str, new_name: str) -> int:
    """Migrate command usage data from an old command name to a new one."""
    affected_count = db.fetch_one("""
        SELECT COUNT(DISTINCT discordId) AS total FROM command_log
        WHERE command = ?
    """, [old_name])["total"]

    db.run("""
        UPDATE command_log
        SET command = ?
        WHERE command = ?
    """, [new_name, old_name])

    return affected_count
