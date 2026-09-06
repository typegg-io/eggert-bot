"""Fill quotes.predictedWpm from the API for every quote already imported.

A quote TypeGG has not rated yet keeps a NULL, which the nWPM model reads as "skip".

    python tools/backfill_predicted_wpm.py            # write
    python tools/backfill_predicted_wpm.py --dry-run  # count only
"""

import asyncio
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from api.quotes import get_quotes  # noqa: E402  needs src on the path

DB = os.path.normpath(os.path.join(HERE, "..", "src", "data", "typegg.db"))
PER_PAGE = 200


async def fetch_ratings() -> dict[str, float]:
    """Return every quote's predictedWpm, keyed by quote ID."""
    ratings = {}
    page = 1
    first = await get_quotes(status="any", per_page=PER_PAGE)
    total_pages = first["totalPages"]

    while True:
        data = first if page == 1 else await get_quotes(status="any", per_page=PER_PAGE, page=page)
        for quote in data["quotes"]:
            predicted = quote.get("predictedWpm")
            if predicted is not None:
                ratings[quote["quoteId"]] = predicted

        print(f"\rFetched page {page}/{total_pages}", end="", file=sys.stderr)
        if page >= total_pages:
            break
        page += 1

    print(file=sys.stderr)

    return ratings


def main() -> int:
    """Backfill the column. Returns a process exit code."""
    dry_run = "--dry-run" in sys.argv

    if not os.path.isfile(DB):
        print(f"database not found at {DB}", file=sys.stderr)
        return 1

    ratings = asyncio.run(fetch_ratings())
    if not ratings:
        print("the API returned no ratings, is SECRET set?", file=sys.stderr)
        return 1

    connection = sqlite3.connect(DB)
    try:
        local = {row[0] for row in connection.execute("SELECT quoteId FROM quotes")}
        pairs = [(rating, quote_id) for quote_id, rating in ratings.items() if quote_id in local]

        print(f"API rated:  {len(ratings):,}")
        print(f"local rows: {len(local):,}")
        print(f"matched:    {len(pairs):,}")
        print(f"unmatched:  {len(local - ratings.keys()):,} local quotes the API did not rate")

        if dry_run:
            return 0

        connection.executemany("UPDATE quotes SET predictedWpm = ? WHERE quoteId = ?", pairs)
        connection.commit()

        filled = connection.execute(
            "SELECT COUNT(*) FROM quotes WHERE predictedWpm IS NOT NULL"
        ).fetchone()[0]
        print(f"filled:     {filled:,}")
    finally:
        connection.close()

    return 0


raise SystemExit(main())
