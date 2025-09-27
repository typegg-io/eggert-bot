from database.typegg import db


def create_user(user_id: str):
    db.run("INSERT INTO users VALUES (?, date('now'))", [user_id])


def get_user(user_id: str):
    return db.fetch_one("SELECT * FROM users WHERE userId = ?", [user_id])

def get_quote_bests(user_id: str, as_dictionary: bool = False):
    results = db.fetch("""
        SELECT quoteId, raceNumber, MAX(pp) AS pp, rawPp, wpm, rawWpm
        FROM races
        WHERE userId = ?
        AND pp > 0
        GROUP BY quoteId
        ORDER BY pp DESC
    """, [user_id])

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results


def delete_user(user_id: str):
    db.run("DELETE FROM users WHERE userId = ?", [user_id])
