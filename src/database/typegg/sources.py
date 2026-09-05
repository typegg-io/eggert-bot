"""The books, songs and films quotes are drawn from."""

import sqlite3

from database.typegg import db


def source_insert(source) -> tuple:
    """Return a source tuple for parameterized inserting."""
    return (
        source["sourceId"],
        source["title"],
        source["author"],
        source["type"],
        source["thumbnailUrl"],
        source["publicationYear"],
    )


def add_sources(sources) -> None:
    """Batch insert or update sources."""
    db.run_many("""
        INSERT INTO sources VALUES (?,?,?,?,?,?)
        ON CONFLICT(sourceId) DO UPDATE SET
            title = excluded.title,
            author = excluded.author,
            type = excluded.type,
            thumbnailUrl = excluded.thumbnailUrl,
            publicationYear = excluded.publicationYear
    """, [source_insert(source) for source in sources])


def add_source(source) -> None:
    """Insert a single source."""
    db.run(f"""
        INSERT OR IGNORE INTO sources
        VALUES ({",".join(["?"] * 6)})
    """, source_insert(source))


def get_sources(as_dictionary=True) -> dict[str, sqlite3.Row] | list[sqlite3.Row]:
    """Return every source, keyed by source ID unless a list is asked for."""
    results = db.fetch("SELECT * FROM sources")

    if as_dictionary:
        return {source["sourceId"]: source for source in results}

    return results


def get_source(source_id: str) -> sqlite3.Row | None:
    """Return a single source entry."""
    return db.fetch_one("SELECT * FROM sources WHERE sourceId = ?", [source_id])


def update_source(source_id: str, updates: dict) -> bool:
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


def delete_source(source_id: str) -> None:
    """
    Delete a source by ID.
    Cascades to delete quotes, races, and keystroke_data.
    """
    db.run("DELETE FROM sources WHERE sourceId = ?", [source_id])
