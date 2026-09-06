"""The most recently queried quote per Discord channel."""

from config import STATS_CHANNEL_ID
from database.bot import db


def get_recent_quote(channel_id: str) -> str | None:
    """Returns the most recently queried quote ID for a Discord channel, or None when there is none."""
    for target in (channel_id, STATS_CHANNEL_ID):
        row = db.fetch_one("""
            SELECT quoteId
            FROM recent_quotes
            WHERE channelId = ?
        """, [target])

        if row:
            return row["quoteId"]

    return None


def set_recent_quote(channel_id: str, quote_id: str) -> None:
    """Updates the recent quote ID for a Discord channel."""
    db.run("""
        INSERT INTO recent_quotes
        VALUES (?, ?)
        ON CONFLICT(channelId) DO UPDATE SET quoteId = excluded.quoteId
    """, [channel_id, quote_id])
