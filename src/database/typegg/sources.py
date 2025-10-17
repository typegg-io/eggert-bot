from database.typegg import db


def source_insert(source):
    """Return a source tuple for parameterized inserting."""
    return (
        source["sourceId"],
        source["title"],
        source["author"],
        source["type"],
        source["thumbnailUrl"],
        source["publicationYear"],
    )


def add_sources(sources):
    """Batch insert sources."""
    db.run_many(f"""
        INSERT OR IGNORE INTO sources
        VALUES ({",".join(["?"] * 6)})
    """, [source_insert(source) for source in sources])


def add_source(source):
    db.run(f"""
        INSERT OR IGNORE INTO sources
        VALUES ({",".join(["?"] * 6)})
    """, source_insert(source))


def get_sources(as_dictionary=True):
    results = db.fetch("SELECT * FROM sources")

    if as_dictionary:
        return {source["sourceId"]: source for source in results}

    return results


def get_source(source_id: str):
    """Return a single source entry."""
    return db.fetch_one("SELECT * FROM sources WHERE sourceId = ?", [source_id])
