"""Seed command_log from the Discord log-channel scrape in src/xtra/log_history.csv.

The CSV carries timestamps but only successful-looking attempts; the frozen users.commands blob
carries exact totals but no dates. Neither alone is right, so this takes timestamps from the CSV,
totals from the blob, and reconciles the two per (user, command) pair:

    cap   drop the CSV rows a pair has beyond its blob count, keeping the most recent
    fill  add undated rows until a pair reaches its blob count

It creates command_log itself, so it can migrate a database pulled from production before the
code that would create it deploys.

    python tools/backfill_command_log.py --dry-run
    python tools/backfill_command_log.py --database /path/to/users-copy.db
"""

import argparse
import csv
import importlib
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

DEFAULT_CSV = os.path.join(ROOT, "src", "xtra", "log_history.csv")
DEFAULT_DATABASE = os.path.join(ROOT, "src", "data", "users.db")

import database.bot  # noqa: E402  needs src on the path first
from database.bot import db as bot_db  # noqa: E402  needs src on the path first
from utils.files import get_command_modules  # noqa: E402  needs src on the path first


def has_command_log(connection: sqlite3.Connection) -> bool:
    """Return whether the target database already carries the command_log table."""
    return connection.execute("""
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'command_log'
    """).fetchone() is not None


def create_command_log(connection: sqlite3.Connection) -> None:
    """Create command_log and its indexes in the target database."""
    live = bot_db.connection
    bot_db.connection = connection
    try:
        # Reloading the schema module runs its DDL against whatever connection bot_db holds.
        importlib.reload(database.bot)
    finally:
        bot_db.connection = live


def build_alias_map() -> dict[str, str]:
    """Return every command name and alias mapped to its canonical name."""
    aliases = {}
    for group, file, module in get_command_modules():
        for name in module.info.all_names:
            aliases[name] = module.info.name

    return aliases


def read_log_rows(csv_path: str, aliases: dict[str, str]) -> tuple[dict, Counter]:
    """Return dated invocations keyed by (discordId, command), plus a tally of what was dropped."""
    rows = defaultdict(list)
    dropped = Counter()

    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["matched"] != "true":
                dropped["unmatched"] += 1
                continue

            content = (row["command"] or "").strip()
            token = content[1:].split()[0].lower() if len(content) > 1 else ""
            command = aliases.get(token)
            if not command:
                dropped["unknown command"] += 1
                continue

            discord_id = row["discord_id"]
            if not discord_id:
                dropped["no discord id"] += 1
                continue

            # The scrape stores RFC-3339 with an offset, which utils.dates cannot parse.
            timestamp = datetime.fromisoformat(row["timestamp"]).timestamp() if row["timestamp"] else None
            if timestamp is None:
                dropped["no timestamp"] += 1
                continue

            # The scrape writes the literal 'dm' where a server ID would go.
            is_dm = row["server_id"] == "dm"
            origin = "dm" if is_dm else "server"
            server_id = None if is_dm else row["server_id"] or None
            rows[(discord_id, command)].append((timestamp, row["user_id"] or None, origin, server_id))

    return rows, dropped


def read_blob_counts(connection: sqlite3.Connection, aliases: dict[str, str]) -> tuple[dict, dict]:
    """Return the frozen blob's counts keyed by (discordId, command), plus each user's TypeGG ID."""
    counts = defaultdict(int)
    user_ids = {}

    for discord_id, user_id, blob in connection.execute("SELECT discordId, userId, commands FROM users"):
        user_ids[discord_id] = user_id
        for name, count in json.loads(blob).get("counts", {}).items():
            if count:
                counts[(discord_id, aliases.get(name, name))] += count

    return counts, user_ids


def reconcile(log_rows: dict, blob_counts: dict, user_ids: dict) -> tuple[list, int, int]:
    """Match the dated rows to the blob totals, returning insert tuples and the cap and fill counts."""
    records = []
    capped = filled = 0

    for key in sorted(set(log_rows) | set(blob_counts)):
        discord_id, command = key
        dated = sorted(log_rows.get(key, []), key=lambda row: row[0])
        target = blob_counts.get(key, 0)

        if len(dated) > target:
            capped += len(dated) - target
            dated = dated[len(dated) - target:]

        for timestamp, user_id, origin, server_id in dated:
            records.append((discord_id, user_id, command, origin, server_id, timestamp))

        shortfall = target - len(dated)
        if shortfall > 0:
            filled += shortfall
            # Counting the pair keeps a filled row's origin and server agreeing with each other.
            common = Counter((row[2], row[3]) for row in dated).most_common(1)
            origin, server_id = common[0][0] if common else ("server", None)
            user_id = user_ids.get(discord_id)
            records.extend([(discord_id, user_id, command, origin, server_id, None)] * shortfall)

    return records, capped, filled


def main() -> int:
    """Reconcile the log against the blob and insert the result. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", default=DEFAULT_DATABASE, help="users.db to write to")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="log_history.csv to read from")
    parser.add_argument("--dry-run", action="store_true", help="report the reconciliation, insert nothing")
    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"no log history at {args.csv}", file=sys.stderr)
        return 1
    if not os.path.isfile(args.database):
        print(f"no database at {args.database}", file=sys.stderr)
        return 1

    connection = sqlite3.connect(args.database)

    if has_command_log(connection):
        existing = connection.execute("SELECT COUNT(*) FROM command_log").fetchone()[0]
        if existing:
            print(f"command_log already holds {existing:,} rows, refusing to double-insert", file=sys.stderr)
            return 1
    elif not args.dry_run:
        create_command_log(connection)
        print(f"created command_log in {args.database}")

    aliases = build_alias_map()
    log_rows, dropped = read_log_rows(args.csv, aliases)
    blob_counts, user_ids = read_blob_counts(connection, aliases)
    records, capped, filled = reconcile(log_rows, blob_counts, user_ids)

    print(f"log rows read     : {sum(len(v) for v in log_rows.values()):,} across {len(log_rows):,} pairs")
    for reason, count in dropped.most_common():
        print(f"  skipped {reason:<16}: {count:,}")
    print(f"blob total        : {sum(blob_counts.values()):,} across {len(blob_counts):,} pairs")
    print(f"capped (dropped)  : {capped:,}")
    print(f"filled (undated)  : {filled:,}")
    print(f"rows to insert    : {len(records):,}")

    if args.dry_run:
        print("\ndry run, nothing written")
        return 0

    with connection:
        connection.executemany("""
            INSERT INTO command_log (discordId, userId, command, origin, serverId, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, records)

    print(f"\ninserted {len(records):,} rows into {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
