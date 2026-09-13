"""Imported quotes and their sources."""

import json
import sqlite3
from json import JSONDecodeError

from api.quotes import calculate_metric, get_all_quotes
from api.sources import get_all_sources
from api.users import get_race
from database.typegg import db
from database.typegg.daily_quotes import update_daily_results_pp, zero_daily_results_pp
from database.typegg.sources import add_sources, get_source
from utils.dates import normalize_datetime
from utils.errors import UnknownQuote
from utils.logging import log, log_server


def quote_insert(quote) -> tuple:
    """Return a quote tuple for parameterized inserting."""
    formatting = quote.get("formatting")
    if formatting is not None and not isinstance(formatting, str):
        formatting = json.dumps(formatting)

    return (
        quote["quoteId"],
        quote.get("source") and quote.get("source").get("sourceId") or quote.get("sourceId"),
        quote["text"],
        quote["explicit"],
        quote["difficulty"],
        quote["complexity"],
        quote["submittedByUsername"],
        quote["ranked"],
        normalize_datetime(quote["created"]),
        quote["language"],
        formatting,
        quote.get("predictedWpm"),
    )


def add_quotes(quotes) -> None:
    """Batch insert or update quotes."""
    db.run_many("""
        INSERT INTO quotes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(quoteId) DO UPDATE SET
            sourceId = excluded.sourceId,
            text = excluded.text,
            explicit = excluded.explicit,
            difficulty = excluded.difficulty,
            complexity = excluded.complexity,
            submittedByUsername = excluded.submittedByUsername,
            ranked = excluded.ranked,
            created = excluded.created,
            language = excluded.language,
            formatting = excluded.formatting,
            predictedWpm = excluded.predictedWpm
    """, [quote_insert(quote) for quote in quotes])


def add_quote(quote) -> None:
    """Insert a single quote."""
    db.run(f"""
        INSERT OR IGNORE INTO quotes
        VALUES ({",".join(["?"] * 12)})
    """, quote_insert(quote))


def get_quotes(
    as_dictionary: bool = True,
    min_difficulty: float = None,
    max_difficulty: float = None,
    min_length: int = None,
    max_length: int = None,
    daily: bool = False,
) -> list[dict] | dict[str, dict]:
    """Returns a list or dictionary of existing quotes."""
    conditions = []
    params = []
    if min_difficulty is not None:
        conditions.append("difficulty >= ?")
        params.append(min_difficulty)
    if max_difficulty is not None:
        conditions.append("difficulty < ?")
        params.append(max_difficulty)
    if min_length is not None:
        conditions.append("LENGTH(text) >= ?")
        params.append(min_length)
    if max_length is not None:
        conditions.append("LENGTH(text) <= ?")
        params.append(max_length)
    if daily:
        conditions.append("quoteId IN (SELECT quoteId FROM daily_quotes)")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    results = db.fetch(f"""
        SELECT *
        FROM quotes
        {where_clause}
    """, params)

    parsed = []
    for quote in results:
        quote = dict(quote)
        if quote["formatting"]:
            try:
                quote["formatting"] = json.loads(quote["formatting"])
            except JSONDecodeError:
                pass
        parsed.append(quote)

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in parsed}

    return parsed


def get_quote(quote_id: str) -> dict:
    """Return a single quote entry with source information."""
    quote = db.fetch_one("""
        SELECT * FROM quotes q
        WHERE quoteId = ?
    """, [quote_id])

    if not quote:
        raise UnknownQuote(quote_id)

    quote = dict(quote)
    source = get_source(quote["sourceId"])
    quote["source"] = source

    if quote.get("formatting"):
        try:
            quote["formatting"] = json.loads(quote["formatting"])
        except (json.JSONDecodeError, TypeError):
            pass

    return quote


def is_quote_id(quote_id: str) -> bool:
    """Returns a boolean whether a quote ID exists or not."""
    result = db.fetch("SELECT 1 FROM quotes WHERE quoteId = ?", [quote_id])
    return bool(result)


async def reimport_quotes() -> None:
    """Refetch every quote from the API and update the local copies."""

    log("Fetching sources")
    async for page_sources in get_all_sources():
        add_sources(page_sources)

    log("Fetching quotes")
    async for page_quotes in get_all_quotes():
        add_quotes(page_quotes)


def get_top_submitters(language: str) -> list[sqlite3.Row]:
    """Return the 100 users who submitted the most ranked quotes in one language."""
    top = db.fetch("""
        SELECT submittedByUsername, COUNT(*) as submissions
        FROM quotes
        WHERE ranked = 1 AND language = ?
        GROUP BY submittedByUsername
        ORDER BY submissions DESC
        LIMIT 100
    """, [language])

    return top


def get_ranked_quote_count(language: str) -> int:
    """Return how many quotes in one language are ranked."""
    result = db.fetch_one("""
        SELECT COUNT(*) AS total FROM quotes
        WHERE ranked = 1 AND language = ?
    """, [language])

    return result["total"]


def get_ranked_quote_chars(language: str) -> int:
    """Return the total character count across ranked quotes in one language."""
    result = db.fetch_one("""
        SELECT SUM(LENGTH(text)) AS total FROM quotes
        WHERE ranked = 1 AND language = ?
    """, [language])

    return result["total"] or 0


async def update_quote(quote_id: str, updates: dict) -> None:
    """
    Update a quote's fields. Only updates provided fields.
    Returns a list of userIds that need reimporting, if ranked changed.
    """
    if not updates:
        return

    if "ranked" in updates:
        current_quote = db.fetch_one("SELECT ranked FROM quotes WHERE quoteId = ?", [quote_id])

        if current_quote:
            old_ranked = current_quote["ranked"]
            new_ranked = updates["ranked"]

            if old_ranked != new_ranked:

                if new_ranked == 0:  # Ranked -> Unranked: Zero out pp values
                    db.run("""
                        UPDATE races
                        SET pp = 0, rawPp = 0
                        WHERE quoteId = ?
                    """, [quote_id])
                    zero_daily_results_pp(quote_id)
                    log_server(f"Quote {quote_id} unranked: Zeroed out pp values")
                elif new_ranked == 1:  # Unranked -> Ranked: Recalculate pp values

                    sample = db.fetch_one("""
                        SELECT userId, raceNumber, wpm
                        FROM races
                        WHERE quoteId = ? AND wpm > 0
                        LIMIT 1
                    """, [quote_id])

                    if sample:  # Derive the ratio from an existing race
                        race_data = await get_race(sample["userId"], sample["raceNumber"])
                        pp_ratio = race_data["pp"] / race_data["wpm"]
                    else:  # No local race to sample, use the calculate pp endpoint
                        calc_result = await calculate_metric(quote_id, 200, "wpm")
                        pp_ratio = calc_result["pp"] / 200

                    db.run("""
                        UPDATE races
                        SET pp = wpm * ?, rawPp = rawWpm * ?
                        WHERE quoteId = ?
                    """, [pp_ratio, pp_ratio, quote_id])
                    update_daily_results_pp(quote_id, pp_ratio)

                    log_server(f"Quote {quote_id} ranked: Updated pp values using ratio {pp_ratio:.4f}")

    fields = [
        "quoteId", "sourceId", "text", "explicit", "difficulty", "complexity",
        "submittedByUsername", "ranked", "created", "language", "formatting",
        "predictedWpm",
    ]
    sets = []
    params = []

    for column in fields:
        if column in updates:
            value = updates[column]
            if column == "formatting" and value is not None and not isinstance(value, str):
                value = json.dumps(value)
            sets.append(f"{column} = ?")
            params.append(value)

    if not sets:
        return

    params.append(quote_id)
    db.run(f"""
        UPDATE quotes
        SET {", ".join(sets)}
        WHERE quoteId = ?
    """, params)


def delete_quote(quote_id: str) -> None:
    """
    Delete a quote by ID.
    Cascades to delete races and keystroke_data via ON DELETE CASCADE.
    """
    db.run("DELETE FROM quotes WHERE quoteId = ?", [quote_id])
