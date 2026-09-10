"""Fill races.nonAfkDuration from the keystrokes already stored for every imported race.

TypeGG grants XP on non-AFK time, which caps each keystroke delay at one second, and the
public API serves only the untrimmed duration. The importer computes the column for new
races; this fills the rows that predate it. A race with no keystroke row keeps a NULL,
which readers coalesce back to duration.

    python tools/backfill_non_afk_duration.py            # write
    python tools/backfill_non_afk_duration.py --dry-run  # count only
"""

import json
import os
import sqlite3
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from utils.stats import calculate_non_afk_duration  # noqa: E402  needs src on the path

DB = os.path.normpath(os.path.join(HERE, "..", "src", "data", "typegg.db"))
BATCH_SIZE = 5000


def read_batch(connection: sqlite3.Connection, after: str) -> list[tuple[str, bytes, int]]:
    """Return the next batch of races missing the column, ordered by race ID."""
    return connection.execute("""
        SELECT r.raceId, k.keystrokeData, k.compressed
        FROM races r
        JOIN keystroke_data k ON k.raceId = r.raceId
        WHERE r.nonAfkDuration IS NULL AND r.raceId > ?
        ORDER BY r.raceId
        LIMIT ?
    """, [after, BATCH_SIZE]).fetchall()


def main() -> int:
    """Backfill the column. Returns a process exit code."""
    dry_run = "--dry-run" in sys.argv

    if not os.path.isfile(DB):
        print(f"database not found at {DB}", file=sys.stderr)
        return 1

    connection = sqlite3.connect(DB)
    try:
        pending = connection.execute("""
            SELECT COUNT(*) FROM races r
            JOIN keystroke_data k ON k.raceId = r.raceId
            WHERE r.nonAfkDuration IS NULL
        """).fetchone()[0]
        print(f"pending:  {pending:,}")

        if dry_run:
            return 0

        after = ""
        done = 0
        failed = 0

        while True:
            rows = read_batch(connection, after)
            if not rows:
                break

            updates = []
            for race_id, payload, compressed in rows:
                if compressed:
                    payload = zlib.decompress(payload)
                duration = calculate_non_afk_duration(json.loads(payload))
                if duration is None:
                    failed += 1
                    continue
                updates.append((duration, race_id))

            connection.executemany(
                "UPDATE races SET nonAfkDuration = ? WHERE raceId = ?", updates
            )
            connection.commit()

            after = rows[-1][0]
            done += len(rows)
            print(f"\rfilled {done:,}/{pending:,}", end="", file=sys.stderr)

        print(file=sys.stderr)
        print(f"filled:   {done - failed:,}")
        print(f"undecodable: {failed:,}")
    finally:
        connection.close()

    return 0


raise SystemExit(main())
