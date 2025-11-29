from typing import Optional

from database.typegg import db


def race_insert(race):
    """Return a race tuple for parameterized inserting."""
    return (
        race["raceId"],
        race["quoteId"],
        race["userId"],
        race["raceNumber"],
        race["pp"],
        race["rawPp"],
        race["wpm"],
        race["rawWpm"],
        race["matchWpm"],
        race["rawMatchWpm"],
        race["duration"],
        race["accuracy"],
        race["errorReactionTime"],
        race["errorRecoveryTime"],
        race["timestamp"] + ".000Z" if "Z" not in race["timestamp"] else race["timestamp"],
        race["stickyStart"],
        race["gamemode"],
        race["placement"],
        race["players"],
        race["completionType"],
    )


def add_races(races):
    """Batch insert user races."""
    db.run_many(f"""
        INSERT OR IGNORE INTO races
        VALUES ({",".join(["?"] * 20)})
    """, [race_insert(race) for race in races])


async def get_races(
    user_id: str,
    columns: list[str] = ["*"],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_number: Optional[int] = None,
    end_number: Optional[int] = None,
    min_pp: Optional[float] = 0,
    max_pp: Optional[float] = 99999,
    gamemode: Optional[str] = None,
    order_by: str = "timestamp",
    reverse: bool = False,
    limit: Optional[int] = None,
    completion_type: Optional[str] = None,
    flags: dict = {},
):
    """Fetch races for a user with optional filters."""
    columns = ",".join(columns)

    if flags:
        status = flags.get("status", "ranked")

        if status != "ranked":
            min_pp = -1
            if status == "unranked":
                max_pp = 0

        metric = flags.get("metric")

        if metric == "raw":
            columns = "rawWpm as wpm, rawPp as pp, " + columns
            if order_by in ["pp", "wpm"]:
                order_by = "raw" + order_by.capitalize()

        gamemode = flags.get("gamemode")

    order = "DESC" if reverse else "ASC"

    conditions = ["userId = ?"]
    params = [user_id]

    if start_number is not None:
        conditions.append(f"raceNumber >= {start_number}")
    if end_number is not None:
        conditions.append(f"raceNumber <= {end_number}")
    if start_date is not None:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("timestamp < ?")
        params.append(end_date)
    if min_pp is not None and gamemode != "multiplayer":
        conditions.append(f"pp > {min_pp}")
    if max_pp is not None:
        conditions.append(f"pp <= {max_pp}")
    if gamemode is not None:
        conditions.append(f"gamemode = ?")
        params.append(gamemode)
        if gamemode == "multiplayer":
            columns = "matchWpm as wpm, rawMatchWpm as rawWpm, " + columns
    if completion_type:
        conditions.append("completionType = ?")
        params.append(completion_type)

    where_clause = "WHERE " + " AND ".join(conditions)

    race_list = []
    batch_size, offset = 100_000, 0

    while True:
        lim = f"LIMIT {limit}" if limit else f"LIMIT {batch_size} OFFSET {offset}"
        batch = await db.fetch_async(f"""
            SELECT {columns}
            FROM races
            {where_clause}
            ORDER BY {order_by} {order}
            {lim}
        """, params)
        race_list.extend(batch)

        if limit or not batch:
            break
        offset += batch_size

    return race_list


def get_quote_races(
    user_id: str,
    quote_id: str,
    order_by: str = "timestamp",
    reverse: bool = False,
):
    """Returns a list of all a user's races for a specific quote."""
    order = "DESC" if reverse else "ASC"

    results = db.fetch(f"""
        SELECT * FROM races
        WHERE userId = ?
        AND quoteId = ?
        ORDER BY {order_by} {order}
    """, [user_id, quote_id])

    return results


def get_latest_race(user_id: str):
    """Returns a user's latest imported race."""
    result = db.fetch_one("""
        SELECT * FROM races
        WHERE userId = ?
        ORDER BY timestamp DESC
        WHERE raceNumber IS NOT NULL
        LIMIT 1
    """, [user_id])

    return result


def delete_races(user_id: str):
    """Deletes all of a user's races."""
    db.run("DELETE FROM races WHERE userId = ?", [user_id])
