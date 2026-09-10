"""Imported races, the largest table in typegg.db."""

import json
import sqlite3
import zlib

from database.typegg import db
from database.typegg.keystroke_data import get_keystroke_data
from utils.dates import normalize_datetime, to_timestamp_string
from utils.errors import RaceNotFound
from utils.flags import Flags, gamemode_filter, is_multiplayer
from utils.stats import calculate_non_afk_duration


def race_insert(race) -> tuple:
    """Return a race tuple for parameterized inserting."""
    timestamp = normalize_datetime(race["timestamp"])
    if "Z" not in timestamp:
        timestamp += ".000Z"
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
        timestamp,
        race["stickyStart"],
        calculate_non_afk_duration(race["keystrokeData"]) if race.get("keystrokeData") else None,
    )


def add_races(races) -> None:
    """Batch insert user races."""
    db.run_many(f"""
        INSERT OR IGNORE INTO races
        VALUES ({",".join(["?"] * 16)})
    """, [race_insert(race) for race in races])


def decompress_keystroke_data(rows) -> list[dict]:
    """Decompress keystroke data in race rows."""
    result = []
    for row in rows:
        row_dict = dict(row)
        keystroke_data = row_dict.get("keystrokeData")
        compressed = row_dict.get("compressed")
        if keystroke_data is not None:
            if compressed == 1:
                keystroke_data = zlib.decompress(keystroke_data)
            row_dict["keystrokeData"] = json.loads(keystroke_data)
        del row_dict["compressed"]
        result.append(row_dict)
    return result


async def get_races(
    user_id: str | None = None,
    columns: list[str] | None = None,
    quote_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_pp: float | None = 0,
    max_pp: float | None = 99999,
    match_id: str | None = None,
    include_dnf: bool | None = True,
    order_by: str | None = "timestamp",
    reverse: bool | None = False,
    limit: int | None = None,
    flags: Flags | None = None,
    get_keystrokes: bool | None = False,
    only_historical_pbs: bool | None = False,
) -> list[sqlite3.Row] | list[dict]:
    """Fetch races for a user with optional filters."""
    columns = list(columns) if columns else ["*"]
    flags = flags or Flags()

    # An explicit argument wins, so -day and the importer keep their own range.
    if flags.date_range and start_date is None and end_date is None:
        start_date, end_date = flags.date_range

    if flags.raw:
        raw_columns = {"wpm": "rawWpm as wpm", "pp": "rawPp as pp"}
        if "*" in columns:
            columns = ["rawWpm as wpm", "rawPp as pp"] + list(columns)
        else:
            columns = [raw_columns.get(column, column) for column in columns]
        if order_by in ["pp", "wpm"]:
            order_by = "raw" + order_by.title()

    columns = ",".join(columns)
    table = "races"

    multiplayer = is_multiplayer(flags)
    # A quit scores 0 pp in a match, so there the quote's own status decides ranked.
    status_by_quote = multiplayer and flags.status != "any"

    # Applying flag filters
    if multiplayer:
        table = "multiplayer_races"
        min_pp = -1
    elif flags.status != "ranked":
        min_pp = -1
        if flags.status == "unranked":
            max_pp = 0

    # WHERE clause
    conditions = []
    params = []

    # Keying this by value would collapse two filters that happen to hold the same one.
    filters = [
        (user_id, "r.userId = ?"),
        (quote_id, "r.quoteId = ?"),
        (to_timestamp_string(start_date), "timestamp >= ?"),
        (to_timestamp_string(end_date), "timestamp < ?"),
        (min_pp, "pp > ?"),
        (max_pp, "pp <= ?"),
        (match_id, "matchId = ?"),
    ]

    for param, condition in filters:
        if param is not None:
            conditions.append(condition)
            params.append(param)

    if flags.gamemode == "solo":
        conditions.append("matchId IS NULL")

    if multiplayer:
        if gamemode := gamemode_filter(flags):
            conditions.append("gamemode = ?")
            params.append(gamemode)
        if not include_dnf:
            conditions.append("completionType NOT IN ('dnf', 'quit')")

    # ORDER clause
    order_clause = f"{order_by} {"DESC" if reverse else "ASC"}"

    # JOIN clause
    join_clauses = []
    if flags.language or status_by_quote:
        join_clauses.append("JOIN quotes q ON q.quoteId = r.quoteId")
        columns = ",".join("r.*" if column == "*" else column for column in columns.split(","))
        columns = columns.replace("quoteId", "r.quoteId")

    if flags.language:
        conditions.append("q.language = ?")
        params.append(flags.language.name)

    if status_by_quote:
        conditions.append("q.ranked = ?")
        params.append(int(flags.status == "ranked"))

    if get_keystrokes:
        join_clauses.append("LEFT JOIN keystroke_data k ON k.raceId = r.raceId")
        columns += ", k.keystrokeData, k.compressed"

    join_clause = " ".join(join_clauses)
    where_clause = "WHERE " + " AND ".join(conditions)

    # Fetching in batches
    batch_size = 100_000
    offset = 0
    race_list = []

    if only_historical_pbs:
        limit_clause = f"LIMIT {limit}" if limit else ""
        batch = await db.fetch_async(f"""
            SELECT *
            FROM (
                SELECT
                    {columns},
                    MAX(wpm) OVER (
                        PARTITION BY r.quoteId
                        ORDER BY timestamp
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) as prev_best_wpm
                FROM {table} r
                {join_clause}
                {where_clause}
            ) subquery
            WHERE wpm > COALESCE(prev_best_wpm, 0)
            ORDER BY {order_clause}
            {limit_clause}
        """, params)
        race_list.extend(batch)
    else:
        # Normal batched fetching
        while True:
            limit_clause = f"LIMIT {limit}" if limit else f"LIMIT {batch_size} OFFSET {offset}"
            batch = await db.fetch_async(f"""
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

    if get_keystrokes:
        return decompress_keystroke_data(race_list)

    return race_list


def get_latest_race(user_id: str) -> sqlite3.Row | None:
    """Returns a user's latest imported race."""
    result = db.fetch_one("""
        SELECT * FROM races
        WHERE userId = ?
        AND raceNumber IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 1
    """, [user_id])

    return result


def get_race(user_id: str, number: int, get_keystrokes: bool = False) -> dict:
    """Return one race by number, raising if the user never ran it."""
    result = db.fetch_one("""
        SELECT * FROM races
        WHERE userId = ?
        AND raceNumber = ?
    """, [user_id, number])

    if result is None:
        raise RaceNotFound(user_id, number)

    race = dict(result)

    if get_keystrokes:
        race["keystrokeData"] = get_keystroke_data(race["raceId"])

    return race


def delete_races(user_id: str) -> None:
    """Deletes all of a user's races."""
    db.run("DELETE FROM races WHERE userId = ?", [user_id])


def get_quote_race_counts(user_id: str) -> list[sqlite3.Row]:
    """Returns a user's quotes by race count."""
    results = db.fetch("""
        SELECT q.text, COUNT(q.text) as races
        FROM races r
        JOIN quotes q on q.quoteId = r.quoteId
        WHERE userId = ?
        GROUP BY q.text
    """, [user_id])

    return results
