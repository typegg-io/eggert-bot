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


async def reimport_daily_results():
    """Re-fetch and replace the leaderboard results for every stored daily quote."""
    from api.daily_quotes import get_daily_quote
    from utils.logging import log

    day_numbers = [row["dayNumber"] for row in db.fetch("SELECT dayNumber FROM daily_quotes ORDER BY dayNumber")]

    for number in day_numbers:
        try:
            log(f"[daily migrate] Re-importing results for daily quote #{number:,}")
            daily_quote = await get_daily_quote(number=number, results=100)
            # Only clear the day's results once we have the new data
            db.run("DELETE FROM daily_quote_results WHERE dayNumber = ?", [number])
            add_daily_results(number, daily_quote["leaderboard"])
        except Exception as e:
            log(f"[daily migrate] Failed for day #{number}: {e.__class__.__name__}: {e}")


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


def get_daily_rank_leaderboard(max_rank: int, exact: bool = False, limit: int = 100):
    """Count how many times each user finished within (or exactly at) max_rank on a daily quote."""
    operator = "=" if exact else "<="
    return db.fetch(f"""
        SELECT userId, username, country, COUNT(*) as count
        FROM daily_quote_results
        WHERE rank {operator} ?
        GROUP BY userId
        ORDER BY count DESC
        LIMIT ?
    """, [max_rank, limit])


def get_user_results(user_id: str):
    return db.fetch("SELECT * FROM daily_quote_results WHERE userId = ?", [user_id])


def get_today_result(user_id: str, quote_id: str):
    """Fetch the user's best race on today's daily quote."""
    today = dates.floor_day(dates.now()).strftime("%Y-%m-%d")
    return db.fetch_one("""
        SELECT pp, wpm FROM races
        WHERE userId = ?
        AND quoteId = ?
        AND timestamp >= ?
        ORDER BY wpm DESC
        LIMIT 1
    """, [user_id, quote_id, today])


def get_user_ranks(user_id: str):
    results = db.fetch("SELECT rank FROM daily_quote_results WHERE userId = ?", [user_id])

    ranks = defaultdict(int)
    for row in results:
        ranks[row["rank"]] += 1

    return ranks
