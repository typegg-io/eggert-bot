"""Aggregate reads over command_log, for the usage dashboard."""

from database.bot import db

# Backfilled rows the log could not date carry a NULL timestamp, so every
# time-series query filters them out rather than bucketing them somewhere wrong.
DATED = "timestamp IS NOT NULL"


def get_totals() -> dict:
    """Return the all-time command count, distinct users, and the dated range."""
    row = db.fetch_one(f"""
        SELECT
            COUNT(*) AS commands,
            COUNT(DISTINCT discordId) AS users,
            COUNT(DISTINCT command) AS distinctCommands,
            MIN(CASE WHEN {DATED} THEN timestamp END) AS firstSeen,
            MAX(CASE WHEN {DATED} THEN timestamp END) AS lastSeen,
            SUM(CASE WHEN origin = 'dm' THEN 1 ELSE 0 END) AS dm,
            SUM(CASE WHEN userId IS NOT NULL THEN 1 ELSE 0 END) AS linked
        FROM command_log
    """)

    return dict(row)


def get_daily_counts(days: int = 365) -> list[dict]:
    """Return the command count and distinct user count for each of the last N days."""
    results = db.fetch(f"""
        SELECT
            date(timestamp, 'unixepoch') AS day,
            COUNT(*) AS commands,
            COUNT(DISTINCT discordId) AS users
        FROM command_log
        WHERE {DATED} AND timestamp > strftime('%s', 'now') - ? * 86400
        GROUP BY day
        ORDER BY day
    """, [days])

    return [dict(row) for row in results]


def get_active_users(days: int) -> int:
    """Return how many distinct users have run a command in the last N days."""
    return db.fetch_one(f"""
        SELECT COUNT(DISTINCT discordId) AS total FROM command_log
        WHERE {DATED} AND timestamp > strftime('%s', 'now') - ? * 86400
    """, [days])["total"]


def get_top_commands(limit: int = 10) -> list[dict]:
    """Return the most used commands, most usages first."""
    results = db.fetch("""
        SELECT command, COUNT(*) AS total FROM command_log
        GROUP BY command
        ORDER BY total DESC
        LIMIT ?
    """, [limit])

    return [dict(row) for row in results]


def get_top_servers(limit: int = 10) -> list[dict]:
    """Return the busiest servers, most commands first. DMs and unplaced rows are excluded."""
    results = db.fetch("""
        SELECT serverId, COUNT(*) AS total, COUNT(DISTINCT discordId) AS users
        FROM command_log
        WHERE serverId IS NOT NULL
        GROUP BY serverId
        ORDER BY total DESC
        LIMIT ?
    """, [limit])

    return [dict(row) for row in results]


def get_command_mix(weeks: int = 26, commands: int = 6) -> dict:
    """Return weekly counts for the top commands, with everything else pooled as 'other'."""
    top = [row["command"] for row in get_top_commands(commands)]
    if not top:
        return {"weeks": [], "buckets": [], "series": {}}

    placeholders = ",".join("?" * len(top))

    results = db.fetch(f"""
        SELECT
            strftime('%Y-%W', timestamp, 'unixepoch') AS week,
            CASE WHEN command IN ({placeholders}) THEN command ELSE 'other' END AS bucket,
            COUNT(*) AS total
        FROM command_log
        WHERE {DATED} AND timestamp > strftime('%s', 'now') - ? * 604800
        GROUP BY week, bucket
        ORDER BY week
    """, [*top, weeks])

    weeks_seen = []
    totals = {}
    for row in results:
        if row["week"] not in weeks_seen:
            weeks_seen.append(row["week"])
        totals[(row["week"], row["bucket"])] = row["total"]

    buckets = [*top, "other"]

    return {
        "weeks": weeks_seen,
        "buckets": buckets,
        "series": {b: [totals.get((w, b), 0) for w in weeks_seen] for b in buckets},
    }


def get_concentration(top: int = 10) -> int:
    """Return how many commands the top N users account for."""
    return db.fetch_one("""
        SELECT COALESCE(SUM(total), 0) AS total FROM (
            SELECT COUNT(*) AS total FROM command_log
            GROUP BY discordId
            ORDER BY total DESC
            LIMIT ?
        )
    """, [top])["total"]


def get_new_users_by_week(weeks: int = 26) -> list[dict]:
    """Return how many users ran their first command in each of the last N weeks."""
    results = db.fetch(f"""
        SELECT week, COUNT(*) AS users FROM (
            SELECT strftime('%Y-%W', MIN(timestamp), 'unixepoch') AS week
            FROM command_log
            WHERE {DATED}
            GROUP BY discordId
        )
        WHERE week >= strftime('%Y-%W', 'now', '-' || ? || ' days')
        GROUP BY week
        ORDER BY week
    """, [weeks * 7])

    return [dict(row) for row in results]
