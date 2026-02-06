from database.typegg import db


def match_insert(match):
    """Return a match tuple for parameterized inserting."""
    return (
        match["matchId"],
        match["quoteId"],
        match["startTime"],
        match["gamemode"],
        match["players"],
    )


def add_matches(match_players):
    """Batch insert matches."""
    db.run_many(f"""
        INSERT OR IGNORE INTO matches
        VALUES ({",".join(["?"] * 5)})
    """, [match_insert(player) for player in match_players])


def delete_matches(user_id: str):
    """Deletes all of a user's matches."""
    db.run("""
        DELETE FROM matches
        WHERE matchId IN (
            SELECT matchId FROM match_results
            WHERE userId = ?
        )
    """, [user_id])
