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


def get_quotes(as_dictionary=True):
    results = db.fetch("SELECT * FROM quotes")

    if as_dictionary:
        return {quote["quoteId"]: quote for quote in results}

    return results
