"""A small pair of databases the slow command regression suite runs against.

Race timestamps are anchored to the current time so -day, -week, -month and -year all find data.
The seed is otherwise deterministic.
"""

import json
import math
import random
import sqlite3
from datetime import UTC, datetime, timedelta

# Lengths span short quotes to a multi-paragraph one, so length filters and graphs have range.
QUOTE_LENGTHS = [54, 56, 64, 75, 84, 133, 176, 822, 1231, 2872]

WORDS = (
    "the quiet river carried a paper boat past old stone bridges while children counted every "
    "lantern glowing along the bank and nobody wanted the evening to end before the music stopped"
).split()

DISCORD_ID = "100000000000000001"
RIVAL_DISCORD_ID = "100000000000000002"
CHANNEL_ID = "900000000000000001"
SERVER_ID = "800000000000000001"
USER_ID = "eiko"
RIVAL_ID = "keegan"
BOT_ID = "bot-nova"

SOURCE_ID = "src-regression"
QUOTE_COUNT = 60
RACE_COUNT = 600
RIVAL_RACE_COUNT = 200
# nWPM needs best races on 50 ranked English quotes, so the corpus is sized around that.
MATCH_COUNT = 80
DAILY_DAYS = 40
SESSION_SIZE = 20

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%fZ"


def marks(count: int) -> str:
    """Return a comma-separated run of SQL placeholders."""
    return ",".join(["?"] * count)


def stamp(date: datetime) -> str:
    """Return a datetime in the string form the race tables store."""
    return date.strftime(TIMESTAMP_FORMAT)


def build_text(length: int, offset: int) -> str:
    """Return a sentence of roughly the given length, cycling through WORDS from an offset."""
    words = []
    i = offset
    while len(" ".join(words)) < length:
        words.append(WORDS[i % len(WORDS)])
        i += 1

    return " ".join(words).capitalize() + "."


def build_keystrokes(text: str, seed: int) -> list:
    """Return a compact keystroke payload that types the text with a corrected typo every 20 characters."""
    rng = random.Random(seed)
    strokes = []
    for i, char in enumerate(text):
        if i and i % 20 == 0:
            strokes.append(f"{rng.randint(40, 90)}+#")
            strokes.append(f"{rng.randint(90, 160)}<")
        strokes.append(f"{0 if i == 0 else rng.randint(40, 90)}+{char}")

    return [1, text, 0, "|".join(strokes)]


def load_quotes() -> list[dict]:
    """Return the quote rows, each carrying a keystroke payload that types its text."""
    quotes = []
    for i in range(QUOTE_COUNT):
        text = build_text(QUOTE_LENGTHS[i % len(QUOTE_LENGTHS)], i)
        payload = build_keystrokes(text, i)

        quotes.append({
            "quoteId": f"q{i + 1}",
            "sourceId": SOURCE_ID,
            "text": text,
            "explicit": 0,
            "difficulty": 1 + (i % 5) * 0.4,
            "complexity": 1 + (i % 3) * 0.3,
            "submittedByUsername": RIVAL_ID,
            # A few quotes are unranked and a few are Spanish, so filters have something to drop.
            "ranked": int(i % 25 != 0),
            "created": stamp(datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=i)),
            "language": "Spanish" if i % 20 == 0 else "English",
            "formatting": None,
            "predictedWpm": 90 + i * 2.5,
            "keystrokeData": payload,
        })

    return quotes


def build_race(rng, quotes, user_id: str, number: int, timestamp: datetime) -> dict:
    """Return one plausible race row."""
    quote = quotes[number % len(quotes)]
    wpm = round(rng.uniform(70, 150), 2)
    pp = round(wpm * quote["difficulty"] * 1.5, 3)

    return {
        "raceId": f"{user_id}-{number}",
        "quoteId": quote["quoteId"],
        "userId": user_id,
        "matchId": None,
        "raceNumber": number,
        "pp": pp,
        "rawPp": round(pp * 1.05, 3),
        "wpm": wpm,
        "rawWpm": round(wpm * rng.uniform(1.01, 1.15), 2),
        # TypeGG stores a race duration in milliseconds.
        "duration": round(len(quote["text"]) * 12000 / wpm, 3),
        "accuracy": round(rng.uniform(0.9, 1.0), 4),
        "errorReactionTime": round(rng.uniform(0, 400), 2),
        "errorRecoveryTime": round(rng.uniform(0, 900), 2),
        "timestamp": stamp(timestamp),
        "stickyStart": int(number % 7 == 0),
    }


def race_times(count: int, now: datetime, span_days: float) -> list[datetime]:
    """Return one timestamp per race, clustered into sessions so a single day holds many."""
    sessions = math.ceil(count / SESSION_SIZE)
    times = []

    for number in range(count):
        start = now - timedelta(days=span_days * (sessions - 1 - number // SESSION_SIZE) / sessions)
        times.append(start + timedelta(minutes=2 * (number % SESSION_SIZE)))

    return times


def build_races(quotes: list[dict], now: datetime) -> tuple[list[dict], list[dict], list[dict]]:
    """Return every race, match and match result the two seeded users share."""
    rng = random.Random(20260906)
    races = []
    matches = []
    results = []

    # Races run from 400 days ago up to now, so every calendar period holds some.
    for number, timestamp in enumerate(race_times(RACE_COUNT, now, 400), start=1):
        races.append(build_race(rng, quotes, USER_ID, number, timestamp))

    for number, timestamp in enumerate(race_times(RIVAL_RACE_COUNT, now, 300), start=1):
        races.append(build_race(rng, quotes, RIVAL_ID, number, timestamp))

    by_number = {race["raceNumber"]: race for race in races if race["userId"] == USER_ID}
    rival_by_number = {race["raceNumber"]: race for race in races if race["userId"] == RIVAL_ID}

    for i in range(MATCH_COUNT):
        match_id = f"m{i + 1}"
        race = by_number[RACE_COUNT - i]
        rival_race = rival_by_number[RIVAL_RACE_COUNT - i]

        race["matchId"] = match_id
        rival_race["matchId"] = match_id
        rival_race["timestamp"] = race["timestamp"]

        matches.append({
            "matchId": match_id,
            "quoteId": race["quoteId"],
            "startTime": race["timestamp"],
            "gamemode": "lobby" if i % 5 == 0 else "quickplay",
            "players": 3,
        })

        field = [
            (USER_ID, None, USER_ID, race["raceNumber"], race),
            (RIVAL_ID, None, RIVAL_ID, rival_race["raceNumber"], rival_race),
            (None, BOT_ID, "Nova", None, race),
        ]
        ranking = sorted(field, key=lambda entry: -entry[4]["wpm"])

        for slot, (user_id, bot_id, username, race_number, source) in enumerate(field):
            results.append({
                "matchId": match_id,
                "userId": user_id,
                "botId": bot_id,
                "username": username,
                "raceNumber": race_number,
                "matchWpm": source["wpm"],
                "rawMatchWpm": source["rawWpm"],
                "matchPp": source["pp"],
                "rawMatchPp": source["rawPp"],
                "startTime": 100 * (slot + 1),
                "accuracy": source["accuracy"],
                "placement": ranking.index(field[slot]) + 1,
                "completionType": "quit" if i % 9 == 0 else "finished",
                "timestamp": source["timestamp"],
            })

    return races, matches, results


def build_daily_quotes(quotes: list[dict], races: list[dict], now: datetime) -> tuple[list[dict], list[dict]]:
    """Return the daily quote rows and the per-user results attached to them."""
    daily = []
    results = []
    user_races = [race for race in races if race["userId"] == USER_ID]
    rival_races = [race for race in races if race["userId"] == RIVAL_ID]

    for offset in range(DAILY_DAYS):
        day_number = 500 - offset
        start = (now - timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        quote = quotes[offset % len(quotes)]

        daily.append({
            "dayNumber": day_number,
            "quoteId": quote["quoteId"],
            "startDate": stamp(start),
            "endDate": stamp(start + timedelta(days=1)),
            "races": 40 + offset,
            "uniqueUsers": 20 + offset,
        })

        for rank, race in enumerate([user_races[-1 - offset], rival_races[-1 - offset]], start=1):
            results.append({
                "dayNumber": day_number,
                "rank": rank,
                "raceId": race["raceId"],
                "quoteId": quote["quoteId"],
                "userId": race["userId"],
                "username": race["userId"],
                "country": "us",
                "raceNumber": race["raceNumber"],
                "pp": race["pp"],
                "rawPp": race["rawPp"],
                "wpm": race["wpm"],
                "rawWpm": race["rawWpm"],
                "duration": race["duration"],
                "accuracy": race["accuracy"],
                "errorReactionTime": race["errorReactionTime"],
                "errorRecoveryTime": race["errorRecoveryTime"],
                "timestamp": stamp(start + timedelta(hours=8)),
                "stickyStart": race["stickyStart"],
                "gamemode": "solo",
            })

    return daily, results


def copy_schema(source: sqlite3.Connection, path) -> sqlite3.Connection:
    """Return a new database carrying the real schema, copied out of a live one."""
    statements = source.execute("""
        SELECT sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    for (statement,) in statements:
        connection.execute(statement)
    connection.commit()

    return connection


def seed_typegg(source: sqlite3.Connection, path, now: datetime) -> sqlite3.Connection:
    """Return a typegg.db carrying the real schema and the regression corpus."""
    connection = copy_schema(source, path)
    quotes = load_quotes()
    races, matches, match_results = build_races(quotes, now)
    daily, daily_results = build_daily_quotes(quotes, races, now)

    connection.execute(f"INSERT INTO sources VALUES ({marks(6)})", [
        SOURCE_ID, "The Regression Corpus", "A. Tester", "book", "https://example.invalid/cover.png", 1998,
    ])

    connection.executemany(f"INSERT INTO users VALUES ({marks(4)})", [
        (USER_ID, int(now.timestamp()), USER_ID, "us"),
        (RIVAL_ID, int(now.timestamp()), RIVAL_ID, "ca"),
    ])

    connection.executemany(f"INSERT INTO quotes VALUES ({marks(12)})", [
        (
            quote["quoteId"], quote["sourceId"], quote["text"], quote["explicit"],
            quote["difficulty"], quote["complexity"], quote["submittedByUsername"],
            quote["ranked"], quote["created"], quote["language"],
            quote["formatting"], quote["predictedWpm"],
        )
        for quote in quotes
    ])

    connection.executemany(f"INSERT INTO races VALUES ({marks(16)})", [
        (
            race["raceId"], race["quoteId"], race["userId"], race["matchId"], race["raceNumber"],
            race["pp"], race["rawPp"], race["wpm"], race["rawWpm"], race["duration"],
            race["accuracy"], race["errorReactionTime"], race["errorRecoveryTime"],
            race["timestamp"], race["stickyStart"], race.get("nonAfkDuration"),
        )
        for race in races
    ])

    payloads = {quote["quoteId"]: json.dumps(quote["keystrokeData"]) for quote in quotes}
    connection.executemany("INSERT INTO keystroke_data VALUES (?, ?, 0)", [
        (race["raceId"], payloads[race["quoteId"]]) for race in races
    ])

    connection.executemany(f"INSERT INTO matches VALUES ({marks(5)})", [
        (m["matchId"], m["quoteId"], m["startTime"], m["gamemode"], m["players"]) for m in matches
    ])

    connection.executemany(f"INSERT INTO match_results VALUES ({marks(14)})", [
        (
            r["matchId"], r["userId"], r["botId"], r["username"], r["raceNumber"],
            r["matchWpm"], r["rawMatchWpm"], r["matchPp"], r["rawMatchPp"], r["startTime"],
            r["accuracy"], r["placement"], r["completionType"], r["timestamp"],
        )
        for r in match_results
    ])

    connection.executemany(f"INSERT INTO daily_quotes VALUES ({marks(6)})", [
        (d["dayNumber"], d["quoteId"], d["startDate"], d["endDate"], d["races"], d["uniqueUsers"])
        for d in daily
    ])

    connection.executemany(f"INSERT INTO daily_quote_results VALUES ({marks(19)})", [
        (
            r["dayNumber"], r["rank"], r["raceId"], r["quoteId"], r["userId"], r["username"],
            r["country"], r["raceNumber"], r["pp"], r["rawPp"], r["wpm"], r["rawWpm"],
            r["duration"], r["accuracy"], r["errorReactionTime"], r["errorRecoveryTime"],
            r["timestamp"], r["stickyStart"], r["gamemode"],
        )
        for r in daily_results
    ])

    connection.execute("INSERT INTO daily_quote_id VALUES (1, ?)", [daily[0]["quoteId"]])

    connection.executemany(f"INSERT INTO quote_leaderboards VALUES ({marks(3)})", [
        row
        for quote in quotes
        for row in [(quote["quoteId"], 1, USER_ID), (quote["quoteId"], 2, RIVAL_ID)]
    ])

    connection.commit()

    return connection


def seed_bot(source: sqlite3.Connection, path, theme: dict, now: datetime) -> sqlite3.Connection:
    """Return a users.db carrying the real schema and two linked Discord users."""
    connection = copy_schema(source, path)
    commands = json.dumps({"counts": {}, "server": 0, "dm": 0})

    connection.executemany(f"INSERT INTO users VALUES ({marks(14)})", [
        (DISCORD_ID, USER_ID, json.dumps(theme), commands, now.timestamp(),
         None, None, 0, 1, 1, 1, "America/New_York", "en", "me"),
        (RIVAL_DISCORD_ID, RIVAL_ID, json.dumps(theme), commands, now.timestamp(),
         None, None, 0, 0, 1, 1, "UTC", "en", "me"),
    ])

    connection.execute("INSERT INTO recent_quotes VALUES (?, ?)", [CHANNEL_ID, "q1"])
    connection.execute("INSERT INTO servers VALUES (?, ?, ?)", [SERVER_ID, "Regression", now.timestamp()])

    connection.executemany("INSERT INTO command_log (discordId, userId, command, origin, serverId, timestamp) "
                           f"VALUES ({marks(6)})", [
        (discord_id, user_id, command, "server", SERVER_ID, (now - timedelta(days=i)).timestamp())
        for i, command in enumerate(["races", "best", "linegraph", "stats", "races", "day"])
        for discord_id, user_id in [(DISCORD_ID, USER_ID), (RIVAL_DISCORD_ID, RIVAL_ID)]
    ])

    connection.commit()

    return connection
