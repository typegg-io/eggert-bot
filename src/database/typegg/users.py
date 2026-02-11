from typing import Optional

from database.typegg import db
from utils.flags import Flags
from utils.logging import log


def create_user(profile: dict):
    db.run("""
        INSERT INTO users
        VALUES (?, date('now'), ?, ?)
    """, [profile["userId"], profile["username"], profile["country"]])


def get_user(user_id: str):
    return db.fetch_one("SELECT * FROM users WHERE userId = ?", [user_id])


def get_user_lookup():
    user_list = db.fetch("SELECT userId, username, country FROM users")
    user_dict = {
        user["userId"]: {
            "username": user["username"],
            "country": user["country"],
        } for user in user_list
    }

    return user_dict


def get_quote_bests(
    user_id: str,
    columns: list[str] = ["*"],
    quote_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_by: Optional[str] = "pp",
    reverse: Optional[bool] = True,
    limit: Optional[int] = None,
    as_dictionary: Optional[bool] = False,
    flags: Flags = Flags(),
):
    """Returns quote bests for a user, with available filters."""
    min_pp = 0
    max_pp = 99999
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

    if multiplayer:
        conditions.append("completionType NOT IN ('dnf', 'quit')")
        conditions.append("gamemode = ?")
        params.append(flags.gamemode)

    # ORDER clause
    order_clause = "DESC" if reverse else "ASC"

    # JOIN clause
    join_clause = ""
    if flags.language:
        join_clause = "JOIN quotes q ON q.quoteId = r.quoteId"
        conditions.append("q.language = ?")
        params.append(flags.language.name)
        columns = columns.replace("quoteId", "r.quoteId")

    where_clause = "WHERE " + " AND ".join(conditions)
    aggregate_column = f"MAX({order_by}) AS {order_by}"
    limit_clause = f"LIMIT {limit}" if limit else ""

    results = db.fetch(f"""
        SELECT {aggregate_column}, {columns}
        FROM {table} r
        {join_clause}
        {where_clause}
        AND pp > {min_pp}
        AND pp <= {max_pp}
        GROUP BY r.quoteId
        ORDER BY {order_by} {order_clause}
        {limit_clause}
    """, params)

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results


def delete_user(user_id: str):
    db.run("DELETE FROM users WHERE userId = ?", [user_id])


async def reimport_users():
    from database.typegg.races import delete_races
    from commands.account.download import run as download
    from api.users import get_profile

    user_list = db.fetch("SELECT userId FROM users")
    for user in user_list:
        user_id = user["userId"]
        try:
            await get_profile(user_id)
        except Exception as e:
            log(f"Failed to migrate user {user_id}: {e.__class__.__name__}")
            continue
        delete_races(user_id)
        delete_user(user_id)

        await download(user_id=user_id)


def get_running_maximum_by_length(user_id: str):
    return db.fetch("""
        WITH text_bests_with_length AS (
            SELECT MAX(r.wpm) AS wpm, LENGTH(q.text) AS length
            FROM races as r
            JOIN quotes q ON q.quoteId = r.quoteId
            WHERE r.userId = ? AND q.ranked
            GROUP BY LENGTH(q.text)
        ),
        running AS (
            SELECT wpm, length, MAX(wpm) OVER (ORDER BY length DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_max_wpm
            FROM text_bests_with_length
        )
        SELECT wpm, length
        FROM running
        WHERE wpm = running_max_wpm
        ORDER BY length;
    """, [user_id])


def get_quotes_over_leaderboard(threshold: int, metric: str = "wpm", limit: int = 100, flags: Flags = Flags()):
    """Returns users with the most quotes over a threshold."""
    min_pp = 0
    max_pp = 99999
    table = "races"

    # Applying flag filters
    if flags.status != "ranked":
        min_pp = -1
        if flags.status == "unranked":
            max_pp = 0

    if flags.raw:
        if metric == "wpm":
            metric = "rawWpm"
        elif metric == "pp":
            metric = "rawPp"

    multiplayer = flags.gamemode in ["quickplay", "lobby"]

    if multiplayer:
        table = "multiplayer_races"

    # WHERE clause
    conditions = []
    params = []

    conditions.append("pp > ?")
    params.append(min_pp)

    conditions.append("pp <= ?")
    params.append(max_pp)

    if flags.gamemode == "solo":
        conditions.append("matchId IS NULL")

    if multiplayer:
        conditions.append("completionType NOT IN ('dnf', 'quit')")
        conditions.append("gamemode = ?")
        params.append(flags.gamemode)

    # JOIN clause
    join_clause = ""
    if flags.language:
        join_clause = "JOIN quotes q ON q.quoteId = r.quoteId"
        conditions.append("q.language = ?")
        params.append(flags.language.name)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    params.append(threshold)

    query = f"""
        SELECT userId, COUNT(*) as count
        FROM (
            SELECT userId, quoteId, MAX({metric}) as best_value
            FROM {table} r
            {join_clause}
            WHERE {where_clause}
            GROUP BY userId, quoteId
        ) as quote_bests
        WHERE best_value >= ?
        GROUP BY userId
        ORDER BY count DESC
        LIMIT {limit}
    """

    return db.fetch(query, params)
