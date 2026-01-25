from collections import defaultdict

from api.daily_quotes import START_DATE
from database.typegg import db
from utils import dates


def add_daily_quote(daily_quote: dict):
    db.run(f"""
        INSERT OR IGNORE INTO daily_quotes
        VALUES ({",".join(["?"] * 6)})
    """, [
        daily_quote["dayNumber"],
        daily_quote["quote"]["quoteId"],
        daily_quote["startDate"],
        daily_quote["endDate"],
        daily_quote["races"],
        daily_quote["uniqueUsers"],
    ])


def daily_result_insert(day_number: int, rank: int, result: dict):
    return (
        day_number,
        rank,
        result["raceId"],
        result["quoteId"],
        result["userId"],
        result["username"],
        result.get("country", None),
        result["raceNumber"],
        result["pp"],
        result["rawPp"],
        result["wpm"],
        result["rawWpm"],
        result["duration"],
        result["accuracy"],
        result["errorReactionTime"],
        result["errorRecoveryTime"],
        result["timestamp"],
        result["stickyStart"],
        result["gamemode"],
    )


def add_daily_results(day_number: int, results: list[dict]):
    """Batch insert daily quote results."""
    db.run_many(f"""
        INSERT OR IGNORE INTO daily_quote_results
        VALUES ({",".join(["?"] * 19)})
    """, [daily_result_insert(day_number, i + 1, result) for i, result in enumerate(results)])


def update_daily_quote_id(quote_id: str):
    db.run("""
        INSERT OR REPLACE INTO daily_quote_id (id, quoteId)
        VALUES (1, ?)
    """, [quote_id])


def get_daily_quote_id():
    row = db.fetch_one("SELECT quoteId FROM daily_quote_id WHERE id = 1")
    return row["quoteId"] if row else None


def get_missing_days():
    results = db.fetch("SELECT dayNumber FROM daily_quotes")
    day_numbers = {row[0] for row in results}
    completed_days = (dates.now() - START_DATE).days
    missing_numbers = [num for num in range(1, completed_days + 1) if num not in day_numbers]

    return missing_numbers


def get_user_results(user_id: str):
    return db.fetch("SELECT * FROM daily_quote_results WHERE userId = ?", [user_id])


def get_user_ranks(user_id: str):
    results = db.fetch("SELECT rank FROM daily_quote_results WHERE userId = ?", [user_id])

    ranks = defaultdict(int)
    for row in results:
        ranks[row["rank"]] += 1

    return ranks
