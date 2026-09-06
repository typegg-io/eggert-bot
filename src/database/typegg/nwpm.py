"""The race streams the nWPM model replays."""

import sqlite3

from database.typegg import db
from utils.nwpm import NwpmState, adjust_race_wpm


def get_qp_races(user_id: str) -> list[sqlite3.Row]:
    """Return a user's quickplay races oldest first, with the quote rating each one adjusts by."""
    # An unrated quote reads 0 so the race counts unadjusted, matching the Go LEFT JOIN.
    return db.fetch("""
        SELECT mr.timestamp, mr.wpm, mr.completionType, COALESCE(q.predictedWpm, 0) AS predictedWpm
        FROM multiplayer_races mr
        LEFT JOIN quotes q ON q.quoteId = mr.quoteId
        WHERE mr.userId = ?
          AND mr.gamemode = 'quickplay'
        ORDER BY mr.timestamp ASC
    """, [user_id])


def get_skill_races(user_id: str) -> list[sqlite3.Row]:
    """Return a user's ranked English races oldest first, the pool the skill median draws from."""
    return db.fetch("""
        SELECT r.timestamp, r.quoteId, r.wpm, q.predictedWpm
        FROM races r
        JOIN quotes q ON q.quoteId = r.quoteId
        WHERE r.userId = ?
          AND q.ranked = 1
          AND q.language = 'English'
          AND r.wpm > 0
          AND q.predictedWpm > 0
        ORDER BY r.timestamp ASC
    """, [user_id])


def quotes_are_rated() -> bool:
    """Return whether any local quote carries the rating nWPM needs."""
    return bool(db.fetch("SELECT 1 FROM quotes WHERE predictedWpm > 0 LIMIT 1"))


def get_nwpm_over_time(user_id: str) -> list[tuple[str, float]]:
    """Return a user's nWPM every time it moved, oldest first, as (timestamp, nWPM) pairs."""
    state = NwpmState()
    points = []
    previous = 0.0

    for timestamp, event in merge_race_streams(user_id):
        if "completionType" in event.keys():
            finished = event["completionType"] == "finished"
            state.window.push(adjust_race_wpm(event["wpm"], event["predictedWpm"]) if finished else 0.0)
        elif not state.skill.update(event["quoteId"], event["wpm"] / event["predictedWpm"]):
            continue

        nwpm = state.recompute()
        if nwpm != previous:
            points.append((timestamp, nwpm))
            previous = nwpm

    return points


def merge_race_streams(user_id: str) -> list[tuple[str, sqlite3.Row]]:
    """Return both race streams interleaved into one chronological list."""
    events = [(row["timestamp"], row) for row in get_qp_races(user_id)]
    events += [(row["timestamp"], row) for row in get_skill_races(user_id)]

    # Truncating to milliseconds makes the two tables' differing precision sort together.
    events.sort(key=lambda event: event[0][:23])

    return events
