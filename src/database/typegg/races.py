from typing import Optional

from database.typegg import db
from utils.flags import Flags


def race_insert(race):
    """Return a race tuple for parameterized inserting."""
    return (
        race["raceId"],
        race["quoteId"],
        race["userId"],
        race.get("matchId"),
        race["raceNumber"],
        race["pp"],
        race.get("rawPp", 0),
        race["wpm"],
        race["rawWpm"],
        race["duration"],
        race["accuracy"],
        race["errorReactionTime"],
        race["errorRecoveryTime"],
        race["timestamp"] + ".000Z" if "Z" not in race["timestamp"] else race["timestamp"],
        race["stickyStart"],
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
    quote_id: str = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_pp: Optional[float] = 0,
    max_pp: Optional[float] = 99999,
    include_dnf: Optional[bool] = True,
    order_by: str = "timestamp",
    reverse: bool = False,
    limit: Optional[int] = None,
    flags: Flags = Flags(),
):
    columns = ",".join(columns)
    table = "races"

    # Applying flag filters
    if flags.status != "ranked":
        min_pp = -1
        if flags.status == "unranked":
            max_pp = 0

    if flags.raw:
        columns = "rawWpm as wpm, rawPp as pp, " + columns
        if order_by in ["pp", "wpm"]:
            order_by = "raw" + order_by.title()

    multiplayer = flags.gamemode in ["quickplay", "lobby"]

    if multiplayer:
        table = "multiplayer_races"
        min_pp = -1

    # WHERE clause
    conditions = ["userId = ?"]
    params = [user_id]

    condition_map = {
        quote_id: "r.quoteId = ?",
        start_date: "timestamp >= ?",
        end_date: "timestamp < ?",
        min_pp: "pp > ?",
        max_pp: "pp <= ?",
    }

    for param, condition in condition_map.items():
        if param is not None:
            conditions.append(condition)
            params.append(param)

    if flags.gamemode == "solo":
        conditions.append("matchId IS NULL")

    if multiplayer and not include_dnf:
        conditions.append("completionType NOT IN ('dnf', 'quit')")

    where_clause = "WHERE " + " AND ".join(conditions)

    # ORDER clause
    order_clause = f"{order_by} {"DESC" if reverse else "ASC"}"

    # JOIN clause
    join_clause = ""
    if flags.language:
        join_clause = "JOIN quotes q ON q.quoteId = r.quoteId"
        conditions.append("q.language = ?")
        params.append(flags.language.name)
        columns = columns.replace("quoteId", "r.quoteId")

    # Fetching in batches
    batch_size = 100_000
    offset = 0
    race_list = []

    while True:
        limit_clause = f"LIMIT {limit}" if limit else f"LIMIT {batch_size} OFFSET {offset}"
        batch = db.fetch(f"""
            SELECT {columns}
            FROM {table} r
            {join_clause}
            {where_clause}
            ORDER BY {order_clause}
            {limit_clause}
        """, params)

        race_list.extend(batch)

        if limit or not batch:
            break

        offset += batch_size

    return race_list


def get_latest_race(user_id: str):
    """Returns a user's latest imported race."""
    result = db.fetch_one("""
        SELECT * FROM races
        WHERE userId = ?
        AND raceNumber IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 1
    """, [user_id])

    return result


def delete_races(user_id: str):
    """Deletes all of a user's races."""
    db.run("DELETE FROM races WHERE userId = ?", [user_id])


def get_quote_race_counts(user_id: str):
    """Returns a user's quotes by race count."""
    results = db.fetch(f"""
        SELECT q.text, COUNT(q.text) as races
        FROM races r
        JOIN quotes q on q.quoteId = r.quoteId
        WHERE userId = ?
        GROUP BY q.text
    """, [user_id])

    return results
