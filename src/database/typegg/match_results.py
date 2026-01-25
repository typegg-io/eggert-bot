from database.typegg import db


def match_result_insert(match_player):
    """Return a match player tuple for parameterized inserting."""
    return (
        match_player["matchId"],
        match_player["userId"],
        match_player["botId"],
        match_player["username"],
        match_player["raceNumber"],
        match_player["matchWpm"],
        match_player["rawMatchWpm"],
        match_player.get("matchPp", 0),
        match_player["rawMatchPp"],
        match_player["startTime"],
        match_player["accuracy"],
        match_player["placement"],
        match_player["completionType"],
        match_player["timestamp"],
    )


def add_match_results(match_players):
    """Batch insert match players."""
    db.run_many(f"""
        INSERT OR IGNORE INTO match_results (
            matchId, userId, botId, username, raceNumber, matchWpm, rawMatchWpm,
            matchPp, rawMatchPp, startTime, accuracy, placement, completionType, timestamp
        )
        VALUES ({",".join(["?"] * 14)})
    """, [match_result_insert(player) for player in match_players])
