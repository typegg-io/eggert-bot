from datetime import datetime, timezone

from database.bot import db
from utils.dates import now as _now


def get_daily_usage(discord_id: str) -> int:
    """Get the current daily usage count for a user, resetting if a new day has started."""
    result = db.fetch_one("SELECT usageCount, lastReset FROM chat_usage WHERE discordId = ?", [discord_id])
    now = _now()

    if not result:
        # First time user, create entry
        db.run("""
            INSERT INTO chat_usage (discordId, usageCount, lastReset)
            VALUES (?, 0, ?)
        """, [discord_id, now.timestamp()])
        return 0

    usage_count = result["usageCount"]
    last_reset = datetime.fromtimestamp(result["lastReset"], timezone.utc)

    # Check if reset is needed for new day
    if now.date() > last_reset.date():
        db.run("""
            UPDATE chat_usage
            SET usageCount = 0, lastReset = ?
            WHERE discordId = ?
        """, [now.timestamp(), discord_id])
        return 0

    return usage_count


def increment_usage(discord_id: str):
    """Increment the usage count for a user."""
    db.run("""
        UPDATE chat_usage
        SET usageCount = usageCount + 1
        WHERE discordId = ?
    """, [discord_id])


def get_remaining_uses(discord_id: str, daily_limit: int) -> int:
    """Get remaining uses for the day."""
    current_usage = get_daily_usage(discord_id)
    return max(0, daily_limit - current_usage)
