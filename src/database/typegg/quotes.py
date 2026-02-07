import json
from json import JSONDecodeError

from api.quotes import get_all_quotes
from api.sources import get_all_sources
from database.typegg import db
from database.typegg.sources import get_source
from utils.errors import UnknownQuote
from utils.logging import log, log_server


def quote_insert(quote):
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
        quote.get("complexity", 0.0),
        quote["submittedByUsername"],
        quote["ranked"],
        quote["created"],
        quote["language"],
        formatting,
    )


def add_quotes(quotes):
    """Batch insert quotes."""
    db.run_many(f"""
        INSERT OR IGNORE INTO quotes
        VALUES ({",".join(["?"] * 11)})
    """, [quote_insert(quote) for quote in quotes])


def add_quote(quote):
    db.run(f"""
        INSERT OR IGNORE INTO quotes
        VALUES ({",".join(["?"] * 11)})
    """, quote_insert(quote))


def get_quotes(
    as_dictionary: bool = True,
    min_difficulty: float = None,
    max_difficulty: float = None,
):
    """Returns a list or dictionary of existing quotes."""
    conditions = []
    params = []
    if min_difficulty is not None:
        conditions.append("difficulty >= ?")
        params.append(min_difficulty)
    if max_difficulty is not None:
        conditions.append("difficulty < ?")
        params.append(max_difficulty)

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


def get_quote(quote_id: str):
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


async def reimport_quotes():
    from database.typegg.sources import add_sources

    log("Fetching sources")
    all_sources = await get_all_sources()
    log("Fetching quotes")
    all_quotes = await get_all_quotes()

    db.run("DELETE FROM quotes")
    db.run("DELETE FROM sources")

    add_sources(all_sources)
    add_quotes(all_quotes)


def get_top_submitters():
    top = db.fetch(f"""
        SELECT submittedByUsername, COUNT(*) as submissions
        FROM quotes
        GROUP BY submittedByUsername
        ORDER BY submissions DESC
        LIMIT 100     
    """)

    return top


def get_ranked_quote_count():
    result = db.fetch_one("""
        SELECT COUNT(*) AS total FROM quotes
        WHERE ranked = 1
    """)

    return result["total"]


async def update_quote(quote_id: str, updates: dict):
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
                    log_server(f"Quote {quote_id} unranked: Zeroed out pp values")
                elif new_ranked == 1:  # Unranked -> Ranked: Calculate pp from sample
                    from api.users import get_race

                    sample = db.fetch_one("""
                        SELECT userId, raceNumber, wpm
                        FROM races
                        WHERE quoteId = ? AND wpm > 0
                        LIMIT 1
                    """, [quote_id])

                    if sample:
                        race_data = await get_race(sample["userId"], sample["raceNumber"])
                        pp_ratio = race_data["pp"] / race_data["wpm"]

                        db.run("""
                            UPDATE races
                            SET pp = wpm * ?, rawPp = rawWpm * ?
                            WHERE quoteId = ?
                        """, [pp_ratio, pp_ratio, quote_id])

                        log_server(f"Quote {quote_id} ranked: Updated pp values using ratio {pp_ratio:.4f}")

    fields = [
        "quoteId", "sourceId", "text", "explicit", "difficulty", "complexity",
        "submittedByUsername", "ranked", "created", "language", "formatting",
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


def delete_quote(quote_id: str):
    """
    Delete a quote by ID.
    Cascades to delete races and keystroke_data via ON DELETE CASCADE.
    """
    db.run("DELETE FROM quotes WHERE quoteId = ?", [quote_id])
