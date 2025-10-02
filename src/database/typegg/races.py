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
        race["duration"],
        race["accuracy"],
        race["errorReactionTime"],
        race["errorRecoveryTime"],
        race["timestamp"],
        race["stickyStart"],
        race["gamemode"],
    )


def add_races(races):
    """Batch insert user races."""
    db.run_many(f"""
        INSERT OR IGNORE INTO races
        VALUES ({",".join(["?"] * 15)})
    """, [race_insert(race) for race in races])


async def get_races(
    user_id: str,
    columns: list[str] = ["*"],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    start_number: Optional[int] = None,
    end_number: Optional[int] = None,
    min_pp: Optional[float] = None,
    max_pp: Optional[float] = None,
    gamemode: Optional[str] = None,
    order_by: str = "timestamp",
    reverse: bool = False,
    limit: Optional[int] = None,
):
    """Fetch races for a user with optional filters."""
    cols = ",".join(columns)
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
    if min_pp is not None:
        conditions.append(f"pp >= {min_pp}")
    if max_pp is not None:
        conditions.append(f"pp < {max_pp}")
    if gamemode is not None:
        conditions.append(f"gamemode = ?")
        params.append(gamemode)

    where_clause = "WHERE " + " AND ".join(conditions)

    race_list = []
    batch_size, offset = 100_000, 0

    while True:
        lim = f"LIMIT {limit}" if limit else f"LIMIT {batch_size} OFFSET {offset}"
        batch = await db.fetch_async(f"""
            SELECT {cols}
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


def get_latest_race_number(user_id: str):
    """Returns a user's latest imported race number."""
    result = db.fetch_one("""
        SELECT raceNumber FROM races
        WHERE userId = ?
        ORDER BY raceNumber DESC
        LIMIT 1
    """, [user_id])

    return result["raceNumber"] if result else 0


def delete_races(user_id: str):
    """Deletes all of a user's races."""
    db.run("DELETE FROM races WHERE userId = ?", [user_id])
