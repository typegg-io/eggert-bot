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


def update_source(source_id: str, updates: dict):
    """Update a source's fields. Only updates provided fields."""
    if not updates:
        return False

    fields = ["sourceId", "title", "author", "type", "thumbnailUrl", "publicationYear"]
    sets = []
    params = []

    for column in fields:
        if column in updates:
            sets.append(f"{column} = ?")
            params.append(updates[column])

    if not sets:
        return False

    params.append(source_id)
    db.run(f"""
        UPDATE sources
        SET {", ".join(sets)}
        WHERE sourceId = ?
    """, params)

    return True


def delete_source(source_id: str):
    """
    Delete a source by ID.
    Cascades to delete quotes, races, and keystroke_data.
    """
    db.run("DELETE FROM sources WHERE sourceId = ?", [source_id])
