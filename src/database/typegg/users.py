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
):
    """Returns quote bests for a user, with available filters."""
    columns = ",".join(columns)
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
        AND pp > 0
        GROUP BY quoteId
        ORDER BY {order_by} {order}
        {limit}
    """, params)

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results


def delete_user(user_id: str):
    db.run("DELETE FROM users WHERE userId = ?", [user_id])
