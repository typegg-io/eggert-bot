from typing import Optional

from database.typegg import db


def create_user(user_id: str):
    db.run("INSERT INTO users VALUES (?, date('now'))", [user_id])


def get_user(user_id: str):
    return db.fetch_one("SELECT * FROM users WHERE userId = ?", [user_id])


def get_quote_bests(
    user_id: str,
    as_dictionary: Optional[bool] = False,
    metric: Optional[str] = "pp",
    reverse: Optional[bool] = True,
    limit: Optional[int] = None,
):
    """Returns quote bests for a user, based on a given metric ('pp' or 'wpm')."""
    aggregate_column = f"MAX({metric}) AS {metric}"
    order_column = metric
    order = "DESC" if reverse else "ASC"
    limit = f"LIMIT {limit}" if limit else ""

    results = db.fetch(f"""
        SELECT
            quoteId, raceNumber, {aggregate_column},
            pp, rawPp, wpm, rawWpm, accuracy, timestamp, gamemode
        FROM races
        WHERE userId = ?
        AND pp > 0
        GROUP BY quoteId
        ORDER BY {order_column} {order}
        {limit}
    """, [user_id])

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results


def delete_user(user_id: str):
    db.run("DELETE FROM users WHERE userId = ?", [user_id])
