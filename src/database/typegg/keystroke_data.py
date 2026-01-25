import json
import zlib

from database.typegg import db


def keystroke_data_insert(race):
    return (
        race["raceId"],
        json.dumps(race["keystrokeData"]),
        0,
    )


def add_keystroke_data(races):
    """Batch insert keystroke data."""

    db.run_many("""
        INSERT OR IGNORE INTO keystroke_data (raceId, keystrokeData, compressed)
        VALUES (?, ?, ?)
    """, [keystroke_data_insert(race) for race in races])


def _decompress(row):
    """Decompress a keystroke data row if needed."""
    if row is None:
        return None
    keystroke_data = row["keystrokeData"]
    if row["compressed"] == 1:
        return zlib.decompress(keystroke_data)
    return keystroke_data


def get_keystroke_data(race_ids: list[str]):
    """Get multiple keystroke data by race IDs, decompressed."""
    if not race_ids:
        return []

    placeholders = ",".join(["?"] * len(race_ids))
    rows = db.fetch(f"""
        SELECT raceId, keystrokeData, compressed FROM keystroke_data
        WHERE raceId IN ({placeholders})
    """, race_ids)

    return {row["raceId"]: _decompress(row) for row in rows}


def delete_keystroke_data(user_id: str):
    """Delete all keystroke data for a user."""
    db.run("""
        DELETE FROM keystroke_data
        WHERE raceId IN (SELECT raceId FROM races WHERE userId = ?)
    """, [user_id])


def get_uncompressed_count():
    """Get the count of uncompressed keystroke data rows."""
    result = db.fetch_one("SELECT COUNT(*) FROM keystroke_data WHERE compressed = 0")
    return result[0] if result else 0


def compress_batch(batch_size: int = 1000):
    """Compress a batch of uncompressed keystroke data. Returns count compressed."""
    rows = db.fetch("""
        SELECT raceId, keystrokeData FROM keystroke_data
        WHERE compressed = 0
        LIMIT ?
    """, [batch_size])

    if not rows:
        return 0

    for row in rows:
        compressed = zlib.compress(row["keystrokeData"].encode("utf-8"), level=6)
        db.run("""
            UPDATE keystroke_data SET keystrokeData = ?, compressed = ?
            WHERE raceId = ?
        """, [compressed, 1, row["raceId"]])

    return len(rows)


async def compress_all(batch_size: int = 1000):
    """Compress all uncompressed keystroke data rows in batches. Yields progress."""
    total = get_uncompressed_count()
    compressed = 0

    while True:
        count = compress_batch(batch_size)
        if count == 0:
            break
        compressed += count
        yield compressed, total
