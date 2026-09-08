"""Daily quotes and their per-user results."""

import sqlite3

from api.daily_quotes import START_DATE, get_daily_quote
from database.typegg import db
from utils import dates
from utils.logging import log


def add_daily_quote(daily_quote: dict) -> None:
    """Insert a daily quote for a day number."""
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


def daily_result_insert(day_number: int, rank: int, result: dict) -> tuple:
    """Return a daily result tuple for parameterized inserting."""
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


def add_daily_results(day_number: int, results: list[dict]) -> None:
    """Batch insert daily quote results."""
    db.run_many(f"""
        INSERT OR IGNORE INTO daily_quote_results
        VALUES ({",".join(["?"] * 19)})
    """, [daily_result_insert(day_number, i + 1, result) for i, result in enumerate(results)])


def zero_daily_results_pp(quote_id: str) -> None:
    """Zero out pp values for a quote's daily results."""
    db.run("""
        UPDATE daily_quote_results
        SET pp = 0, rawPp = 0
        WHERE quoteId = ?
    """, [quote_id])


def update_daily_results_pp(quote_id: str, pp_ratio: float) -> None:
    """Recalculate pp values for a quote's daily results from a wpm:pp ratio."""
    db.run("""
        UPDATE daily_quote_results
        SET pp = wpm * ?, rawPp = rawWpm * ?
        WHERE quoteId = ?
    """, [pp_ratio, pp_ratio, quote_id])


async def reimport_daily_results() -> None:
    """Re-fetch and replace the leaderboard results for every stored daily quote."""

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


def update_daily_quote_id(quote_id: str) -> None:
    """Set the quote ID served as today's daily."""
    db.run("""
        INSERT OR REPLACE INTO daily_quote_id (id, quoteId)
        VALUES (1, ?)
    """, [quote_id])


def get_daily_quote_id() -> str | None:
    """Return today's daily quote ID, if one is set."""
    row = db.fetch_one("SELECT quoteId FROM daily_quote_id WHERE id = 1")
    return row["quoteId"] if row else None


def get_missing_days() -> list[int]:
    """Return the day numbers that have no daily quote yet."""
    results = db.fetch("SELECT dayNumber FROM daily_quotes")
    day_numbers = {row[0] for row in results}
    completed_days = (dates.now() - START_DATE).days
    missing_numbers = [num for num in range(1, completed_days + 1) if num not in day_numbers]

    return missing_numbers


def get_daily_rank_leaderboard(max_rank: int, exact: bool = False, limit: int = 100) -> list[sqlite3.Row]:
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


def get_user_results(user_id: str) -> list[sqlite3.Row]:
    """Return every daily quote result for a user."""
    return db.fetch("SELECT * FROM daily_quote_results WHERE userId = ?", [user_id])


def get_today_result(user_id: str, quote_id: str, raw: bool = False) -> sqlite3.Row | None:
    """Fetch the user's best race on today's daily quote."""
    today = dates.floor_day(dates.now()).strftime("%Y-%m-%d")
    columns = "rawPp AS pp, rawWpm AS wpm" if raw else "pp, wpm"
    return db.fetch_one(f"""
        SELECT {columns} FROM races
        WHERE userId = ?
        AND quoteId = ?
        AND timestamp >= ?
        ORDER BY wpm DESC
        LIMIT 1
    """, [user_id, quote_id, today])
