from database.bot import db


def get_recent_quote(channel_id: str):
    """Returns the most recently queried quote ID for a Discord channel."""
    quote_id = db.fetch_one("""
        SELECT quoteId
        FROM recent_quotes
        WHERE channelId = ?
    """, [channel_id])

    return quote_id[0]


def set_recent_quote(channel_id: str, quote_id: str):
    """Updates the recent quote ID for a Discord channel."""
    db.run("""
        INSERT INTO recent_quotes
        VALUES (?, ?)
        ON CONFLICT(channelId) DO UPDATE SET quoteId = excluded.quoteId
    """, [channel_id, quote_id])
