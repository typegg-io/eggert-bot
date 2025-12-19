import json
from typing import Counter

from database.bot import db
from utils import dates
from utils.colors import DEFAULT_THEME


def _parse_counts(commands_json: str):
    """Parse the commands JSON string and return the counts dict."""
    return json.loads(commands_json).get("counts", {})


def add_user(discord_id: str):
    user = {
        "discordId": discord_id,
        "userId": None,
        "theme": json.dumps(DEFAULT_THEME),
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
    }
    user_values = user.values()

    db.run(f"INSERT INTO users VALUES ({",".join(["?"] * len(user_values))})", list(user_values))

    return user


def get_user(discord_id: str, auto_insert: bool = True):
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


def get_user_ids():
    users = db.fetch("SELECT discordId FROM users")

    return [int(user[0]) for user in users]


def get_command_usage(user_id: int):
    """Return command counts for a single user."""
    results = db.fetch("SELECT commands FROM users WHERE discordId = ?", [user_id])
    return _parse_counts(results[0]["commands"]) if results else {}


def get_all_command_usage():
    """Return total command counts across all users."""
    all_commands = db.fetch("SELECT commands FROM users")
    counter = Counter()

    for user in all_commands:
        counter.update(_parse_counts(user["commands"]))

    return dict(counter)


def get_command_usage_by_user():
    """Return a list of per-user command counts."""
    all_commands = db.fetch("SELECT discordId, commands FROM users")
    return [
        {"discord_id": user["discordId"], "commands": _parse_counts(user["commands"])}
        for user in all_commands
    ]


def get_top_users_by_command_usage():
    """Return users sorted by total command usage."""
    users = db.fetch("SELECT discordId, commands FROM users")

    top_users = [{
        "discord_id": user["discordId"],
        "total_commands": sum(_parse_counts(user["commands"]).values()),
    } for user in users]

    return sorted(top_users, key=lambda u: u["total_commands"], reverse=True)


def get_theme(discord_id: int):
    """Returns a user's theme if they exist."""
    results = db.fetch("SELECT theme FROM users WHERE discordId = ?", [discord_id])

    return json.loads(results[0]["theme"]) if results else None


def update_commands(discord_id: str, command_name: str, origin: str):
    """
    Increments a user's command count.
    Args:
        discord_id: Discord ID of the user
        command_name: Name of the command used
        origin: Origin of the command ('server', 'dm')
    """
    user_commands = db.fetch("""
        SELECT commands FROM users
        WHERE discordId = ?
    """, [discord_id])[0][0]

    user_commands = json.loads(user_commands)

    if command_name in user_commands["counts"]:
        user_commands["counts"][command_name] += 1
    else:
        user_commands["counts"][command_name] = 1
    user_commands[origin] += 1

    db.run("""
        UPDATE users
        SET commands = ?
        WHERE discordId = ?
    """, [json.dumps(user_commands), discord_id])


def update_theme(discord_id: str, theme: dict):
    db.run("""
        UPDATE users
        SET theme = ?
        WHERE discordId = ?
    """, [json.dumps(theme), discord_id])


def update_warning(discord_id: str):
    db.run("""
        UPDATE users
        SET isPrivacyWarned = 1
        WHERE discordId = ?
    """, [discord_id])


def update_gg_plus_status(user_id: str, is_gg_plus: bool):
    """Update a user's GG+ subscription status."""
    db.run("""
        UPDATE users
        SET isGgPlus = ?
        WHERE userId = ?
    """, [1 if is_gg_plus else 0, user_id])


def link_user(discord_id: str, user_id: str):
    """Creates a link between a Discord ID and a User ID."""
    db.run("""
        UPDATE users
        SET userId = ?
        WHERE discordId = ?
    """, [user_id, discord_id])


def unlink_user(discord_id: str):
    """Removes the link between a Discord ID and a User ID."""
    db.run("""
        UPDATE users
        SET userId = NULL
        WHERE discordId = ?
    """, [discord_id])


def get_all_linked_users():
    """Returns a dictionary of user IDs and Discord ID."""
    results = db.fetch("""
        SELECT discordId, userId
        FROM users
        WHERE userId IS NOT NULL
    """)

    return {str(row["userId"]): str(row["discordId"]) for row in results}


def is_user_linked(discord_id: str) -> bool:
    """Check if a Discord user is linked to a user ID."""
    results = db.fetch("""
        SELECT userId
        FROM users
        WHERE discordId = ? AND userId IS NOT NULL
    """, [discord_id])

    return len(results) > 0


def ban_user(discord_id: str):
    db.run("""
        UPDATE users
        SET isBanned = 1
        WHERE discordId = ?
    """, [discord_id])


def unban_user(discord_id: str):
    db.run("""
        UPDATE users
        SET isBanned = 0
        WHERE discordId = ?
    """, [discord_id])


def admin_user(discord_id: str):
    db.run("""
        UPDATE users
        SET isAdmin = 1
        WHERE discordId = ?
    """, [discord_id])


def unadmin_user(discord_id: str):
    db.run("""
        UPDATE users
        SET isAdmin = 0
        WHERE discordId = ?
    """, [discord_id])


def get_admin_users():
    results = db.fetch("""
        SELECT discordId FROM users
        WHERE isAdmin = 1
    """)

    return results


def get_discord_id(user_id: str):
    result = db.fetch_one("SELECT discordId FROM users WHERE userId = ?", [user_id])
    if not result:
        return None

    return result["discordId"]
