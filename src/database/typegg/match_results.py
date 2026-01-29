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
        INSERT OR IGNORE INTO match_results
        VALUES ({",".join(["?"] * 14)})
    """, [match_result_insert(player) for player in match_players])


def get_encounter_stats(user_id: str, gamemode: str = None):
    """Get all opponents a user has faced in multiplayer matches with head-to-head stats."""
    conditions = ["userId = ?"]
    params = [user_id]

    if gamemode:
        conditions.append("gamemode = ?")
        params.append(gamemode)

    where_clause = "WHERE " + " AND ".join(conditions)

    results = db.fetch(f"""
        SELECT
            matchId,
            opponentUsername,
            isBot,
            COUNT(*) as totalEncounters,
            SUM(CASE WHEN userPlacement < opponentPlacement THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN userPlacement > opponentPlacement THEN 1 ELSE 0 END) as losses,
            MAX(timestamp) AS lastEncounter
        FROM encounters
        {where_clause}
        GROUP BY opponentId, opponentUsername
        ORDER BY totalEncounters DESC
    """, params)

    return results


def get_match_stats(user_id: str, gamemode: str = None):
    conditions = ["userId = ?"]
    params = [user_id]

    if gamemode:
        conditions.append("gamemode = ?")
        params.append(gamemode)

    where_clause = "WHERE " + " AND ".join(conditions)

    results = db.fetch_one(f"""
        SELECT
            COUNT(DISTINCT matchId) AS totalMatches,
            COUNT(DISTINCT CASE WHEN userPlacement = 1 THEN matchId END) AS matchWins
        FROM encounters
        {where_clause}
    """, params)

    return results


def get_opponent_encounters(user_id: str, opponent_id: str, gamemode: str = None):
    """Get all finished encounters between two users."""
    conditions = [
        "userId = ?", "opponentId = ?",
        "NOT userDnf", "NOT opponentDnf"
    ]
    params = [user_id, opponent_id]

    if gamemode:
        conditions.append("AND m.gamemode = ?")
        params.append(gamemode)

    where_clause = "WHERE " + " AND ".join(conditions)

    matches = db.fetch(f"""
        SELECT * FROM encounters
        {where_clause}
        ORDER BY timestamp ASC
    """, params)

    return matches
