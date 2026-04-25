import asyncio
from typing import Optional

from database.typegg import db
from utils.errors import ProfileNotFound
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
    min_wpm: Optional[float] = None,
    max_wpm: Optional[float] = None,
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

    having_conditions = []
    if min_wpm is not None:
        having_conditions.append("MAX(wpm) >= ?")
        params.append(min_wpm)
    if max_wpm is not None:
        having_conditions.append("MAX(wpm) < ?")
        params.append(max_wpm)
    having_clause = "HAVING " + " AND ".join(having_conditions) if having_conditions else ""

    results = db.fetch(f"""
        SELECT {aggregate_column}, {columns}
        FROM {table} r
        {join_clause}
        {where_clause}
        AND pp > {min_pp}
        AND pp <= {max_pp}
        GROUP BY r.quoteId
        {having_clause}
        ORDER BY {order_by} {order_clause}
        {limit_clause}
    """, params)

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results


def delete_user(user_id: str):
    db.run("DELETE FROM users WHERE userId = ?", [user_id])


def delete_user_data(user_id: str):
    """Delete all data associated with a user, recomputing affected leaderboards."""
    from database.typegg.quote_leaderboards import remove_user_from_leaderboards
    from database.typegg.match_results import delete_match_results

    remove_user_from_leaderboards(user_id)
    delete_match_results(user_id)
    delete_user(user_id)


async def reimport_users():
    from commands.account.download import run as download

    user_list = db.fetch("SELECT userId FROM users")
    max_retries = 3

    for user in user_list:
        user_id = user["userId"]
        delete_user_data(user_id)

        for attempt in range(1, max_retries + 1):
            try:
                await download(user_id=user_id)
                break
            except ProfileNotFound:
                log(f"[user migrate] Profile not found for {user_id}, skipping")
            except Exception as e:
                log(f"Failed to migrate user {user_id} (attempt {attempt}/{max_retries}): {e.__class__.__name__}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(5)
                else:
                    log(f"[user migrate] Skipping user {user_id} after {max_retries} failed attempts")


async def reimport_nwpm():
    from api.core import request
    from api.users import get_profile
    from database.bot.users import get_all_linked_users
    from utils.errors import ProfileNotFound

    linked_users = get_all_linked_users()

    for user_id in linked_users:
        try:
            log(f"[nwpm migrate] Updating nWPM for {user_id}")
            profile = await get_profile(user_id)
            await request(
                url="http://localhost:8888/update-nwpm-role",
                json_data={"userId": user_id, "nWpm": profile["stats"]["nWpm"]},
                method="POST",
            )
        except ProfileNotFound:
            log(f"[nwpm migrate] Profile not found for {user_id}, skipping")
        except Exception as e:
            log(f"[nwpm migrate] Failed for {user_id}: {e.__class__.__name__}: {e}")


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
