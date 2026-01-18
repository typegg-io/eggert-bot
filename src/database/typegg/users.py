from typing import Optional

from database.typegg import db
from utils.logging import log
from utils.strings import LANGUAGES


def create_user(user_id: str):
    db.run("INSERT INTO users VALUES (?, date('now'))", [user_id])


def get_user(user_id: str):
    return db.fetch_one("SELECT * FROM users WHERE userId = ?", [user_id])


def get_quote_bests(
    user_id: str,
    columns: list[str] = ["*"],
    quote_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_by: Optional[str] = "pp",
    gamemode: Optional[str] = None,
    language: Optional[str] = None,
    reverse: Optional[bool] = True,
    limit: Optional[int] = None,
    as_dictionary: Optional[bool] = False,
    flags: Optional[dict] = {},
):
    """Returns quote bests for a user, with available filters."""

    columns = ",".join(columns)
    min_pp = 0
    max_pp = 99999

    if flags:
        status = flags.get("status", "ranked")

        if status != "ranked":
            min_pp = -1
            if status == "unranked":
                max_pp = 0
                order_by = "wpm"

        metric = flags.get("metric")

        if metric == "raw":
            columns = "rawWpm as wpm, rawPp as pp, " + columns
            if order_by in ["pp", "wpm"]:
                order_by = "raw" + order_by.capitalize()

        gamemode = flags.get("gamemode")
        language = flags.get("language")

    aggregate_column = f"MAX({order_by}) AS {order_by}"
    order = "DESC" if reverse else "ASC"
    limit = f"LIMIT {limit}" if limit else ""

    conditions = ["userId = ?"]
    params = [user_id]

    if quote_id is not None:
        conditions.append("r.quoteId = ?")
        params.append(quote_id)
    if start_date is not None:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("timestamp < ?")
        params.append(end_date)
    if gamemode is not None and gamemode in ["solo", "quickplay", "lobby"]:
        conditions.append("gamemode = ?")
        params.append(gamemode)
        if gamemode == "quickplay":
            columns = "matchWpm as wpm, rawMatchWpm as rawWpm, matchPp as pp, rawMatchPp as rawPp, " + columns
            if order_by in ["pp", "wpm"]:
                aggregate_column = aggregate_column.replace(order_by, "match" + order_by.title())

    join_clause = ""
    if language is not None and language in LANGUAGES:
        join_clause = "JOIN quotes q ON q.quoteId = r.quoteId"
        conditions.append("q.language = ?")
        params.append(LANGUAGES.get(language))
        columns = columns.replace("quoteId", "r.quoteId")

    where_clause = "WHERE " + " AND ".join(conditions)

    results = db.fetch(f"""
        SELECT {aggregate_column}, {columns}
        FROM races r
        {join_clause}
        {where_clause}
        AND pp > {min_pp}
        AND pp <= {max_pp}
        GROUP BY r.quoteId
        ORDER BY {order_by} {order}
        {limit}
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
