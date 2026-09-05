"""Scrape the Discord bot log channel into src/xtra/log_history.csv.

Every command the bot has logged is one message in that channel, carrying a timestamp the
users.commands blob never held. tools/backfill_command_log.py turns the result into command_log
rows, so this is the only source of dates for anything that ran before that table existed.

    python tools/backscan_logs.py             # walk back from the newest message, overwriting
    python tools/backscan_logs.py --resume    # continue an interrupted walk further back
    python tools/backscan_logs.py --catchup   # walk forwards from the newest CSV row to now

Needs BOT_TOKEN and LOG_CHANNEL_ID in .env. The CSV it writes stays gitignored.
"""

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DEFAULT_CSV = os.path.join(ROOT, "src", "xtra", "log_history.csv")

MAX_RETRIES = 8
BATCH_SLEEP = 1.1
TOTAL_MESSAGES = 275634  # Set this to the channel message count for an ETA.

# Constants

DISCORD_API = "https://discord.com/api/v10"
MESSAGES_URL = f"{DISCORD_API}/channels/{{channel_id}}/messages"

CSV_FIELDS = ["timestamp", "message_id", "server_id", "channel_id", "discord_id", "user_id", "command", "matched"]

# Inverse of ADMIN_ALIASES in src/utils/logging.py.
# The zero-width spaces in the first three keys are load-bearing.
ADMIN_ID_BY_ALIAS: dict[str, int] = {
    "K​eegan":   155481579005804544,
    "E​iko":     87926662364160000,
    "A​evistar": 808803618005188651,
    # Pre-aa00e4d names, used in the channel before 2025-11-15.
    "Keegan":     155481579005804544,
    "Eiko":       87926662364160000,
    "Fragment":   808803618005188651,
}

# Groups:
#   1 → server_id (None for DM)
#   2 → channel_id (None for DM)
#   3 → bold admin name (None if regular user)
#   4 → discord_id from <@id> (None if admin)
#   5 → linked TypeGG user_id (optional)
#   6 → command content
LOG_RE = re.compile(
    r"^(?:https://discord\.com/channels/(\d+)/(\d+)/\d+|\[DM\])"
    r" "
    r"(?:\*\*(.+?)\*\*|<@!?(\d+)>)"
    r"(?: \(([^)]+)\))?"
    r": `(.+)`$",
    re.DOTALL,
)

# Discord API

def _headers() -> dict:
    """Return the authorization header for a bot request."""
    return {"Authorization": f"Bot {BOT_TOKEN}"}


def fetch_messages(channel_id: str, before: str | None = None, after: str | None = None) -> list[dict]:
    """Return one batch of channel messages, retrying through rate limits."""
    url = MESSAGES_URL.format(channel_id=channel_id)
    params: dict = {"limit": 100}
    if before:
        params["before"] = before
    if after:
        params["after"] = after

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)

        if resp.status_code == 200:
            remaining   = resp.headers.get("X-RateLimit-Remaining")
            reset_after = resp.headers.get("X-RateLimit-Reset-After")
            if remaining is not None and int(remaining) == 0 and reset_after is not None:
                wait = float(reset_after) + 0.05
                print(f"\n  bucket exhausted, sleeping {wait:.2f}s")
                time.sleep(wait)
            return resp.json()

        if resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 1.0))
                scope = "global" if data.get("global", False) else "route"
            except Exception:
                retry_after = 2.0
                scope = "unknown"
            print(f"\n  429 rate limited ({scope}), waiting {retry_after:.2f}s")
            time.sleep(retry_after + 0.1)
            continue

        if resp.status_code == 401:
            sys.exit("invalid bot token (401), set BOT_TOKEN correctly")
        if resp.status_code == 403:
            sys.exit("bot lacks Read Message History permission (403)")
        if resp.status_code == 404:
            sys.exit(f"channel {channel_id} not found (404)")

        print(f"\n  HTTP {resp.status_code} on attempt {attempt}/{MAX_RETRIES}, "
              f"retrying in {backoff:.1f}s")
        time.sleep(backoff)
        backoff = min(backoff * 2, 60.0)

    sys.exit(f"failed after {MAX_RETRIES} retries")


# Message parsing

def parse_log_message(msg: dict) -> dict | None:
    """Return one CSV record for a log-channel message, or None if it is not a log line."""
    content = (msg.get("content") or "").strip()
    m = LOG_RE.match(content)
    if not m:
        return None

    admin_name = m.group(3)
    raw_discord_id = m.group(4)

    if raw_discord_id:
        discord_id = raw_discord_id
    elif admin_name:
        resolved = ADMIN_ID_BY_ALIAS.get(admin_name)
        discord_id = str(resolved) if resolved else ""
    else:
        discord_id = ""

    return {
        "timestamp":  msg.get("timestamp", ""),
        "message_id": msg.get("id", ""),
        "server_id":  m.group(1) or "dm",
        "channel_id": m.group(2) or "dm",
        "discord_id": discord_id,
        "user_id":    m.group(5) or "",
        "command":    m.group(6),
        "matched":    "true",
    }


# Resume support

def newest_id_in_csv(csv_path: Path) -> str | None:
    """Return the largest (most recent) snowflake stored in an existing CSV."""
    if not csv_path.exists():
        return None
    newest: str | None = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row.get("message_id", "")
            if mid and (newest is None or int(mid) > int(newest)):
                newest = mid
    return newest


def oldest_id_in_csv(csv_path: Path) -> str | None:
    """Return the smallest (oldest) snowflake stored in an existing CSV."""
    if not csv_path.exists():
        return None
    oldest: str | None = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row.get("message_id", "")
            if mid and (oldest is None or int(mid) < int(oldest)):
                oldest = mid
    return oldest


def count_rows_in_csv(csv_path: Path) -> int:
    """Return how many rows an existing CSV already holds."""
    if not csv_path.exists():
        return 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


# Entry point

def format_progress(rate: float, scanned: int, catchup: bool) -> str:
    """Return the progress suffix for a batch line, with an ETA when the channel total is known."""
    if catchup or not TOTAL_MESSAGES or rate <= 0:
        return f"{rate:.1f} msg/s"

    seconds = (TOTAL_MESSAGES - scanned) / rate
    if seconds >= 3600:
        eta = f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    else:
        eta = f"{int(seconds // 60)}m {int(seconds % 60)}s"

    return f"{scanned / TOTAL_MESSAGES * 100:.1f}% | ETA {eta}"


def main() -> int:
    """Scan the log channel into the CSV. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--channel", default=LOG_CHANNEL_ID, help="log channel ID, overriding the env var")
    parser.add_argument("--output", default=DEFAULT_CSV, help="CSV to write to")
    parser.add_argument("--resume", action="store_true", help="continue an interrupted walk from the oldest row")
    parser.add_argument("--catchup", action="store_true", help="walk forwards from the newest row to the present")
    args = parser.parse_args()

    channel_id = args.channel.strip()
    output_path = Path(args.output)

    if not BOT_TOKEN:
        print("BOT_TOKEN is not set, add it to .env", file=sys.stderr)
        return 1
    if not channel_id:
        print("no channel ID, set LOG_CHANNEL_ID in .env or pass --channel", file=sys.stderr)
        return 1
    if args.catchup and args.resume:
        print("--resume and --catchup walk opposite directions, pick one", file=sys.stderr)
        return 1

    if args.catchup:
        if not output_path.exists():
            print(f"--catchup needs an existing {output_path} to continue from", file=sys.stderr)
            return 1
        catchup_cursor = newest_id_in_csv(output_path)
        before_cursor = None
        already_scanned = count_rows_in_csv(output_path)
        file_mode = "a"
        write_header = False
        print(f"catching up from message ID {catchup_cursor} ({already_scanned:,} rows already in CSV)")
    elif args.resume and output_path.exists():
        catchup_cursor = None
        before_cursor = oldest_id_in_csv(output_path)
        already_scanned = count_rows_in_csv(output_path)
        file_mode = "a"
        write_header = False
        print(f"resuming from message ID {before_cursor} ({already_scanned:,} rows already in CSV)")
    else:
        catchup_cursor = None
        before_cursor = None
        already_scanned = 0
        file_mode = "w"
        write_header = True
        if output_path.exists():
            print(f"overwriting existing {output_path}")

    total_fetched = 0
    total_parsed = 0
    total_skipped = 0
    scan_start = time.time()

    print(f"\nbackscanning channel {channel_id} into {output_path}\n")

    with open(output_path, file_mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()

        while True:
            batch = fetch_messages(channel_id, before=before_cursor, after=catchup_cursor)

            if not batch:
                break

            # Discord always returns newest first, so a forward walk reads its batches backwards.
            for msg in reversed(batch) if args.catchup else batch:
                total_fetched += 1

                record = parse_log_message(msg)
                if record:
                    writer.writerow(record)
                    total_parsed += 1
                else:
                    writer.writerow({
                        "timestamp": msg.get("timestamp", ""),
                        "message_id": msg.get("id", ""),
                        "matched": "false",
                    })
                    total_skipped += 1

            if args.catchup:
                edge = batch[0]
                catchup_cursor = edge["id"]
            else:
                edge = batch[-1]
                before_cursor = edge["id"]

            elapsed = time.time() - scan_start
            rate = total_fetched / elapsed if elapsed > 0 else 0
            progress = format_progress(rate, total_fetched + already_scanned, args.catchup)

            print(f"  fetched {total_fetched:>6,} messages | at {edge.get("timestamp", "")[:10]} | {progress}",
                  flush=True)

            time.sleep(BATCH_SLEEP)

    print("\n\ndone.")
    print(f"  total messages fetched   : {total_fetched:,}")
    print(f"  log entries written      : {total_parsed:,}")
    print(f"  non-log messages skipped : {total_skipped:,}")
    print(f"  output                   : {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
