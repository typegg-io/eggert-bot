from typing import Optional

from database.typegg import db


def create_user(user_id: str):
    db.run("INSERT INTO users VALUES (?, date('now'))", [user_id])


def get_user(user_id: str):
    return db.fetch_one("SELECT * FROM users WHERE userId = ?", [user_id])


def get_quote_bests(
    user_id: str,
    columns: list[str] = ["*"],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    order_by: Optional[str] = "pp",
    gamemode: Optional[str] = None,
    reverse: Optional[bool] = True,
    limit: Optional[int] = None,
    as_dictionary: Optional[bool] = False,
    flags: dict = {},
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
            columns = columns.replace("wpm", "rawWpm as wpm")
            columns = columns.replace("pp", "rawPp as pp")
            if order_by in ["pp", "wpm"]:
                order_by = "raw" + order_by.capitalize()

        gamemode = flags.get("gamemode")

    aggregate_column = f"MAX({order_by}) AS {order_by}"
    order = "DESC" if reverse else "ASC"
    limit = f"LIMIT {limit}" if limit else ""

    conditions = ["userId = ?"]
    params = [user_id]

    if start_date is not None:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("timestamp < ?")
        params.append(end_date)
    if gamemode is not None and gamemode in ["solo", "multiplayer"]:
        conditions.append("gamemode = ?")
        params.append(gamemode)

    where_clause = "WHERE " + " AND ".join(conditions)

    results = db.fetch(f"""
        SELECT {aggregate_column}, {columns}
        FROM races
        {where_clause}
        AND pp > {min_pp}
        AND pp <= {max_pp}
        GROUP BY quoteId
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

    user_list = db.fetch("SELECT userId FROM users")
    for user in user_list:
        user_id = user["userId"]
        delete_races(user_id)
        delete_user(user_id)

        await download(user_id=user_id)
