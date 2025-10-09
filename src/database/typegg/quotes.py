from database.typegg import db


def quote_insert(quote):
    """Return a quote tuple for parameterized inserting."""
    return (
        quote["quoteId"],
        quote["source"]["sourceId"],
        quote["text"],
        quote["explicit"],
        quote["difficulty"],
        quote["submittedByUsername"],
        quote["ranked"],
        quote["created"],
    )


def add_quotes(quotes):
    """Batch insert quotes."""
    db.run_many(f"""
        INSERT OR IGNORE INTO quotes
        VALUES ({",".join(["?"] * 8)})
    """, [quote_insert(quote) for quote in quotes])


def add_quote(quote):
    db.run(f"""
        INSERT OR IGNORE INTO quotes
        VALUES ({",".join(["?"] * 8)})
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

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results
