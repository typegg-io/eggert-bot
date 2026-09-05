"""Multiplayer match rows."""

from database.typegg import db
from utils.dates import normalize_datetime


def match_insert(match) -> tuple:
    """Return a match tuple for parameterized inserting."""
    return (
        match["matchId"],
        match["quoteId"],
        normalize_datetime(match["startTime"]),
        match["gamemode"],
        match["players"],
    )


def add_matches(match_players) -> None:
    """Batch insert matches."""
    db.run_many(f"""
        INSERT OR IGNORE INTO matches
        VALUES ({",".join(["?"] * 5)})
    """, [match_insert(player) for player in match_players])
