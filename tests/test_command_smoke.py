"""Invoke every stats command against a seeded database and assert it renders.

Slow: it runs matplotlib for real, so it is deselected from the default pytest run.

    pytest -m slow

Nothing here asserts on content. It exists to catch the failure the fast suite structurally
cannot see, a command that raises the moment it is invoked.
"""

import asyncio
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import matplotlib
import pytest
import seed_data
from discord.ext.commands import CommandError, CommandInvokeError

from bot_setup import parse_flags
from commands.base import Command
from database.bot import db as bot_db
from database.typegg import db as typegg_db
from error_handler import ErrorHandler
from utils.colors import DEFAULT_THEME
from utils.dates import resolve_date_range
from utils.errors import BotError, NoRacesFiltered, NotSubscribed
from utils.flags import apply_universe_status, resolve_universe

matplotlib.use("Agg")

pytestmark = pytest.mark.slow

NOW = datetime.now(UTC)

# One invocation per line, written the way a user types it.
INVOCATIONS = [
    "-activity",
    "-average",
    "-average eiko",
    "-bestaverages",
    "-bestaverages -raw",
    "-bestaverages pp",
    "-bestaverages acc",
    "-best",
    "-best -wpm",
    "-best attempts",
    "-best playtime",
    "-best attempts any",
    "-bestgraph",
    "-bestgraph -pp",
    "-commandleaderboard",
    "-comparegraph eiko keegan",
    "-comparegraph eiko keegan daily",
    "-comparegraph eiko keegan 0-15 daily",
    "-comparegraph eiko keegan 0-15 >50c",
    "-comparegraph eiko keegan <500c",
    "-dailygraph",
    "-dailygraph raw",
    "-dailyleaderboard",
    "-dailyleaderboard raw",
    "-dailystats",
    "-dailystats raw",
    "-day",
    "-encounters",
    "-endurance",
    "-endurance raw",
    "-fastestcompletion 20",
    "-fc 50 pp",
    "-histogram",
    "-leaderboard qo 100",
    "-leaderboard firsts",
    "-lb podium -solo",
    "-lb top10s -fr",
    "-improvement",
    "-improvement acc",
    "-simp acc",
    "-keystrokes",
    "-ks azerty",
    "-keystrokelog",
    "-kl 1",
    "-lastonline",
    "-lengthgraph",
    "-lengthgraph raw",
    "-linegraph",
    "-linegraph nwpm",
    "-linegraph level",
    "-linegraph playtime",
    "-longestaverage 100",
    "-longestbreak",
    "-marathon",
    "-marathon pp 1h",
    "-matchgraph",
    "-milestone 5",
    "-ms 100 wpm",
    "-ms 50 pp",
    "-month",
    "-personalbestgraph",
    "-pbg -wpm",
    "-pbg solo",
    "-positionstats",
    "-pplength",
    "-pplength raw",
    "-quote q1",
    "-qp q1",
    "-quoteimprovements",
    "-qi wpm best",
    "-quoteleaderboard q1",
    "-qlb q1 raw",
    "-quoteranks",
    "-qr eiko 1",
    "-quotesover 100",
    "-quotestrength",
    "-quotestrength raw",
    "-racecompare",
    "-racecompare 60 120",
    "-rc q1 1 -1",
    "-racegraph",
    "-racehistory",
    "-racehistory raw",
    "-races",
    "-segments",
    "-session",
    "-session time 1h",
    "-stats",
    "-sumofbest",
    "-sumofbest raw",
    "-timetravel",
    "-topgraph q1",
    "-10g q1 raw",
    "-toptens",
    "-unraced",
    "-ur keegan",
    "-week",
    "-worst",
    "-year",
]

# Raw pp is the whole output, so a non-subscriber is refused outright.
RAW_PP_REFUSED = [
    "-bestaverages pp raw",
    "-best raw",
    "-bestgraph raw",
    "-comparegraph eiko keegan raw",
    "-histogram raw",
    "-improvement -pp raw",
    "-lengthgraph raw",
    "-linegraph raw",
    "-pbg raw",
    "-pplength raw",
    "-quotesover 100 raw",
    "-quotestrength raw",
    "-worst raw",
]

# Raw pp is one field, so a non-subscriber still gets the page with the GG+ link in its place.
RAW_PP_SUBSTITUTED = [
    "-average",
    "-bestaverages -raw",
    "-best -wpm raw",
    "-best attempts raw",
    "-dailyleaderboard raw",
    "-dailystats raw",
    "-qlb q1 raw",
    "-racegraph",
    "-racehistory raw",
]

# The whole command is a GG+ feature.
GG_PLUS_REFUSED = [
    "-calculatepp",
    "-sumofbest",
    "-unraced",
]

# Commands left out, and the reason each one cannot run here.
SKIPPED = {
    "about": "static embed, no data path",
    "admin": "moderation, needs a real Discord member",
    "art": "reads message attachments",
    "ban": "moderation, needs a real Discord member",
    "brothers": "static embed, no data path",
    "calculatepp": "the pp formula lives behind the API",
    "calculator": "arithmetic on raw args, no data path",
    "chat": "calls Anthropic",
    "dashboard": "admin, renders from live production counts",
    "database": "admin, reports on the real database file",
    "define": "calls a dictionary API",
    "deferbug": "admin, needs a forum thread",
    "deleteuser": "admin, destructive",
    "download": "admin-adjacent, writes a file from the live API",
    "echo": "admin, needs a channel to speak into",
    "exportbugs": "admin, needs a forum channel",
    "forcelink": "admin, needs a real Discord member",
    "help": "static embed, covered by test_command_registry",
    "link": "starts a verification flow",
    "lockdown": "admin, mutates global bot state",
    "migrate": "admin, rewrites the database",
    "ping": "reports the websocket latency",
    "profilepicture": "renders a Discord avatar",
    "redownload": "re-imports from the live API",
    "renamecommand": "admin, rewrites the command log",
    "resolvebug": "admin, needs a forum thread",
    "restart": "admin, exits the process",
    "roles": "needs a real guild",
    "rundaily": "admin, posts the daily quote",
    "say": "admin, needs a channel to speak into",
    "search": "served entirely by the API",
    "setuniverse": "mutates the invoking user",
    "settings": "mutates the invoking user",
    "support": "static embed, no data path",
    "theme": "mutates the invoking user",
    "thonk": "static embed, no data path",
    "translate": "restricted to the general channel",
    "unadmin": "moderation, needs a real Discord member",
    "unban": "moderation, needs a real Discord member",
    "unlink": "mutates the invoking user",
    "update": "admin, pulls from git",
    "whois": "resolves Discord members",
}


# Fakes


class FakeMessage:
    """The message object a send returns, enough for edits and reactions."""

    def __init__(self) -> None:
        """Start with no attachments and a fixed id."""
        self.id = 1
        self.attachments = []

    async def edit(self, **kwargs) -> "FakeMessage":
        """Accept an edit and return itself."""
        return self

    async def delete(self) -> None:
        """Accept a delete."""

    async def add_reaction(self, emoji) -> None:
        """Accept a reaction."""

    async def reply(self, *args, **kwargs) -> "FakeMessage":
        """Accept a reply and return a new message."""
        return FakeMessage()


class FakeTyping:
    """The async context manager `ctx.typing()` returns."""

    async def __aenter__(self) -> "FakeTyping":
        """Enter the typing indicator."""
        return self

    async def __aexit__(self, *args) -> bool:
        """Leave the typing indicator."""
        return False


class FakeContext:
    """A BotContext stand-in that records what a command sends."""

    def __init__(self, invocation: str, user: dict, bot) -> None:
        """Parse an invocation the way `get_context` does and record nothing yet."""
        flags, cleaned, explicit = parse_flags(invocation)

        self.flags = flags
        self.explicit_flags = explicit
        self.raw_args = tuple(invocation.split()[1:])
        self.args = tuple(cleaned.split()[1:])
        self.invoked_with = invocation.split()[0].lstrip("-")
        self.user = user
        self.bot = bot
        self.prefix = "-"
        self.id = 1
        self.message = FakeMessage()
        self.sent = []

        self.author = SimpleNamespace(
            id=int(seed_data.DISCORD_ID),
            name=seed_data.USER_ID,
            display_name="Eiko",
            mention=f"<@{seed_data.DISCORD_ID}>",
            roles=[],
            display_avatar=SimpleNamespace(url="https://example.invalid/avatar.png"),
            send=self._record,
        )
        self.channel = SimpleNamespace(id=int(seed_data.CHANNEL_ID), send=self._record)
        self.guild = SimpleNamespace(id=1, name="Regression", roles=[])

    async def _record(self, *args, **kwargs) -> FakeMessage:
        """Record one outgoing message and return a stand-in for it."""
        if args:
            kwargs["content"] = args[0]
        self.sent.append(kwargs)
        return FakeMessage()

    async def send(self, *args, **kwargs) -> FakeMessage:
        """Record a send from a command or from `Message.send`."""
        return await self._record(*args, **kwargs)

    def typing(self) -> FakeTyping:
        """Return the typing indicator context manager."""
        return FakeTyping()


def fake_profile(user_id: str, races: int) -> dict:
    """Return a Profile-shaped dict for a seeded user."""
    return {
        "userId": user_id,
        "username": user_id,
        "displayName": user_id.title(),
        "avatarUrl": "https://example.invalid/avatar.png",
        "country": "us",
        "globalRank": 4,
        "countryRank": 2,
        "joinDate": seed_data.stamp(NOW - timedelta(days=500)),
        "lastSeen": seed_data.stamp(NOW),
        "profileViews": 321,
        "isGgPlus": True,
        "subscribeDate": seed_data.stamp(NOW - timedelta(days=60)),
        "hardware": {"layout": "QWERTY", "keyboard": "Wooting 60HE", "switches": "Lekker"},
        "stats": {
            "races": races,
            "soloRaces": races - seed_data.MATCH_COUNT,
            "quickplayRaces": seed_data.MATCH_COUNT,
            "quotesTyped": len(seed_data.QUOTE_LENGTHS),
            "charactersTyped": 480000.0,
            "wins": 12,
            "playTime": 90000.0,
            "level": 42.5,
            "experience": 425000.0,
            "accuracy": 0.964,
            "nWpm": 118.4,
            "totalPp": 21000.0,
            "bestPp": {"value": 240.0},
            "bestWpm": {"value": 168.0},
            "dailyQuotes": {"streak": 6, "bestStreak": 19, "completed": seed_data.DAILY_DAYS},
            "firsts": 3,
            "podiums": 7,
            "topTens": 11,
        },
    }


PROFILES = {
    seed_data.USER_ID: fake_profile(seed_data.USER_ID, seed_data.RACE_COUNT),
    seed_data.RIVAL_ID: fake_profile(seed_data.RIVAL_ID, seed_data.RIVAL_RACE_COUNT),
}


QUOTES = {quote["quoteId"]: quote for quote in seed_data.load_quotes()}

RACES, MATCHES, MATCH_RESULTS = seed_data.build_races(list(QUOTES.values()), NOW)
RACES_BY_NUMBER = {(race["userId"], race["raceNumber"]): race for race in RACES}


def api_quote_stats(user_id: str, quote_id: str) -> dict:
    """Return one user's attempt and play time counters for a quote, as the API serves them."""
    races = [race for race in RACES if race["userId"] == user_id and race["quoteId"] == quote_id]
    completion = sum(race["duration"] for race in races)

    return {
        "races": len(races),
        "attempts": len(races) + 3,
        "playTime": completion + 4200,
        "completionPlayTime": completion,
        "attemptPlayTime": 4200,
        "globalRank": 4,
        "margin": 1.25,
    }


def api_quote_counters(user_id: str, params: dict | None) -> dict:
    """Return a user's quotes ranked by a lifetime counter, as the API serves them."""
    quote_counters = []

    for quote_id in QUOTES:
        races = [race for race in RACES if race["userId"] == user_id and race["quoteId"] == quote_id]
        if not races:
            continue

        quote_counters.append(
            api_quote_stats(user_id, quote_id) | {
                "quote": api_quote(quote_id),
                "bestRace": max(races, key=lambda race: race["wpm"]),
            }
        )

    params = params or {}
    sort = params.get("sort", "attempts")
    quote_counters.sort(key=lambda counters: -counters.get(sort, 0))

    page = int(params.get("page", 1))
    per_page = int(params.get("perPage", 10))

    return {
        "page": page,
        "perPage": per_page,
        "totalPages": max(1, -(-len(quote_counters) // per_page)),
        "totalCount": len(quote_counters),
        "quotes": quote_counters[(page - 1) * per_page:page * per_page],
    }


def api_quote(quote_id: str) -> dict:
    """Return one seeded quote in the shape the API serves it."""
    quote = QUOTES[quote_id]

    return {
        "quoteId": quote["quoteId"],
        "text": quote["text"],
        "difficulty": quote["difficulty"],
        "complexity": quote["complexity"],
        "ranked": bool(quote["ranked"]),
        "explicit": bool(quote["explicit"]),
        "language": quote["language"],
        "created": quote["created"],
        "submittedByUsername": quote["submittedByUsername"],
        "formatting": None,
        "predictedWpm": quote["predictedWpm"],
        "races": 1200,
        "uniqueUsers": 300,
        "leaderboard": [
            leaderboard_entry(race, position)
            for position, race in enumerate(sorted(
                [race for race in RACES if race["quoteId"] == quote_id],
                key=lambda race: -race["wpm"],
            )[:10], start=1)
        ],
        "source": {
            "sourceId": seed_data.SOURCE_ID,
            "title": "The Regression Corpus",
            "author": "A. Tester",
            "type": "book",
            "thumbnailUrl": "https://example.invalid/cover.png",
            "publicationYear": 1998,
        },
    }


def leaderboard_entry(race: dict, position: int) -> dict:
    """Return one seeded race in the shape a quote leaderboard entry takes."""
    return {
        "rank": position,
        "userId": race["userId"],
        "username": race["userId"],
        "displayName": race["userId"].title(),
        "country": "us",
        "isGgPlus": race["userId"] == seed_data.USER_ID,
        "raceNumber": race["raceNumber"],
        "pp": race["pp"],
        "rawPp": race["rawPp"],
        "wpm": race["wpm"],
        "rawWpm": race["rawWpm"],
        "accuracy": race["accuracy"],
        "timestamp": race["timestamp"],
    }


def api_race(user_id: str, race_number: int) -> dict:
    """Return one seeded race in the shape the API serves it, match field included."""
    race = RACES_BY_NUMBER[(user_id, race_number)]
    payload = dict(race)
    payload.update({
        "username": user_id,
        "displayName": user_id.title(),
        "country": "us",
        "isGgPlus": user_id == seed_data.USER_ID,
        "keystrokeData": QUOTES[race["quoteId"]]["keystrokeData"],
    })

    if race["matchId"] is None:
        payload["match"] = None
        return payload

    match = next(entry for entry in MATCHES if entry["matchId"] == race["matchId"])
    players = [
        {
            **result,
            "displayName": result["username"].title(),
            "country": "us",
            "isGgPlus": result["userId"] == seed_data.USER_ID,
            "keystrokeData": QUOTES[match["quoteId"]]["keystrokeData"],
        }
        for result in MATCH_RESULTS if result["matchId"] == race["matchId"]
    ]

    payload["match"] = {**match, "players": players}

    return payload


def daily_payload() -> dict:
    """Return today's daily quote with a leaderboard both seeded users placed on."""
    quote_id = QUOTES["q1"]["quoteId"]
    start = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    leaderboard = [
        {
            "rank": rank,
            "raceId": f"{user_id}-1",
            "quoteId": quote_id,
            "userId": user_id,
            "username": user_id,
            "displayName": user_id.title(),
            "country": "us",
            "raceNumber": rank,
            "pp": 220.0 - rank,
            "rawPp": 230.0 - rank,
            "wpm": 140.0 - rank,
            "rawWpm": 150.0 - rank,
            "duration": 12.5,
            "accuracy": 0.98,
            "errorReactionTime": 120.0,
            "errorRecoveryTime": 240.0,
            "timestamp": seed_data.stamp(start + timedelta(hours=8)),
            "stickyStart": False,
            "gamemode": "solo",
            "isGgPlus": True,
            "keystrokeData": QUOTES[quote_id]["keystrokeData"],
        }
        for rank, user_id in enumerate([seed_data.USER_ID, seed_data.RIVAL_ID], start=1)
    ]

    return {
        "dayNumber": 500,
        "startDate": seed_data.stamp(start),
        "endDate": seed_data.stamp(start + timedelta(days=1)),
        "quote": api_quote(quote_id),
        "races": 812,
        "uniqueUsers": 214,
        "leaderboard": leaderboard,
    }


RACE_TOTALS = {
    seed_data.USER_ID: seed_data.RACE_COUNT,
    seed_data.RIVAL_ID: seed_data.RIVAL_RACE_COUNT,
}


async def fake_request(url: str, params: dict = None, **kwargs) -> dict:
    """Answer the API calls the seeded commands make, and name any that is unaccounted for."""
    if url.endswith("/v1/daily"):
        return daily_payload()

    # The leaderboard writes its rank and formatter into each row.
    if url.endswith("/v1/leaders"):
        return {"users": [dict(profile) for profile in PROFILES.values()]}

    for user_id, profile in PROFILES.items():
        if url.endswith(f"/users/{user_id}"):
            return profile
        if url.endswith(f"/users/{user_id}/races"):
            return {"races": [{"raceNumber": RACE_TOTALS[user_id]}], "page": 1, "perPage": 20}
        if url.endswith(f"/users/{user_id}/quotes"):
            return api_quote_counters(user_id, params)
        if f"/users/{user_id}/quotes/" in url:
            return api_quote_stats(user_id, url.rsplit("/", 1)[-1])
        if url.endswith(f"/users/{user_id}/quote-rankings"):
            return {
                "quotesTyped": seed_data.QUOTE_COUNT,
                "positionCounts": {str(rank): 6 - rank // 2 for rank in range(1, 11)},
            }

    for user_id in PROFILES:
        if f"/users/{user_id}/races/" in url:
            return api_race(user_id, int(url.rsplit("/", 1)[-1]))

    if "/v1/quotes/" in url:
        return api_quote(url.rsplit("/", 1)[-1])

    raise AssertionError(f"the regression suite has no canned response for {url}")


# Fixtures


@pytest.fixture(scope="session")
def seeded(tmp_path_factory):
    """Point both databases at a seeded copy and stub the API and the importer out."""
    patch = pytest.MonkeyPatch()
    directory = tmp_path_factory.mktemp("regression")

    typegg = seed_data.seed_typegg(typegg_db.reader, directory / "typegg.db", NOW)
    users = seed_data.seed_bot(bot_db.connection, directory / "users.db", DEFAULT_THEME, NOW)

    patch.setattr(typegg_db, "reader", typegg)
    patch.setattr(typegg_db, "writer", typegg)
    patch.setattr(typegg_db, "file", str(directory / "typegg.db"))
    patch.setattr(bot_db, "connection", users)

    for module in _api_modules():
        patch.setattr(module, "request", fake_request)

    async def no_import(self, ctx, profile) -> None:
        """Stand in for the auto-import every profile lookup would otherwise trigger."""

    patch.setattr(Command, "import_user", no_import)

    yield SimpleNamespace(typegg=typegg, users=users)

    patch.undo()
    typegg.close()
    users.close()


def _api_modules() -> list:
    """Return every api module that imported `request` by name."""
    import importlib

    names = ["daily_quotes", "leaders", "quotes", "races", "sources", "users"]
    return [importlib.import_module(f"api.{name}") for name in names]


def build_user() -> dict:
    """Return the seeded user in the shape the global check leaves on the context."""
    row = bot_db.fetch_one("SELECT * FROM users WHERE discordId = ?", [seed_data.DISCORD_ID])
    user = dict(row)
    user["theme"] = json.loads(user["theme"])
    user["theme"]["isGgPlus"] = user["isGgPlus"]
    user["timezone"] = ZoneInfo(user["timezone"])
    return user


def find_command(name: str):
    """Return the cog class and discord.py Command for one command name or alias."""
    from discord.ext import commands as discord_commands

    from utils.files import get_command_modules

    for group, file, module in get_command_modules():
        for obj in module.__dict__.values():
            if not (isinstance(obj, type) and issubclass(obj, Command) and obj is not Command):
                continue
            for value in vars(obj).values():
                if isinstance(value, discord_commands.Command) and name in [value.name, *value.aliases]:
                    return obj, value

    raise LookupError(f"no command named {name}")


async def invoke(
    invocation: str,
    stored=(None, None),
    universe: str | None = None,
    gg_plus: bool = True,
    admin: bool = False,
) -> FakeContext:
    """Run one invocation end to end and return the context it sent through."""
    name = invocation.split()[0].lstrip("-")
    cog_class, command = find_command(name)
    user = build_user()
    user["isAdmin"] = admin
    user["isGgPlus"] = gg_plus
    user["theme"]["isGgPlus"] = gg_plus
    ctx = FakeContext(invocation, user, bot=SimpleNamespace(get_channel=lambda _: None))

    ctx.flags.date_range = resolve_date_range(ctx.flags, ctx.user["timezone"], stored)
    ctx.flags.language = resolve_universe(ctx.flags, universe or ctx.user["universe"])
    apply_universe_status(ctx.flags)

    cog = cog_class(ctx.bot)
    await cog.cog_before_invoke(ctx)
    await command.callback(cog, ctx, *accepted_args(command, ctx.args))

    return ctx


def accepted_args(command, args: tuple) -> tuple:
    """Return the arguments the callback takes, dropping extras the way ignore_extra does."""
    params = list(command.clean_params.values())

    if any(param.kind is param.VAR_POSITIONAL for param in params):
        return args

    return args[:len(params)]


# Tests


def test_every_command_is_either_exercised_or_skipped(command_classes):
    """A new command file has to join the suite or say why it cannot."""
    from discord.ext import commands as discord_commands

    registered_commands = [
        value
        for classes in command_classes.values()
        for cls in classes
        for value in vars(cls).values()
        if isinstance(value, discord_commands.Command)
    ]
    registered = {value.name for value in registered_commands}
    names = {alias: value.name for value in registered_commands for alias in [value.name, *value.aliases]}
    invoked = {line.split()[0].lstrip("-") for line in INVOCATIONS}
    covered = {names.get(token, token) for token in invoked} | set(SKIPPED)

    assert sorted(registered - covered) == []
    assert sorted(covered - registered) == []


@pytest.mark.parametrize("invocation", INVOCATIONS)
def test_a_command_renders(seeded, invocation):
    """Every command sends something and raises nothing."""
    ctx = asyncio.run(invoke(invocation))

    assert ctx.sent, f"{invocation} sent nothing"


@pytest.mark.parametrize("invocation", INVOCATIONS)
def test_a_command_renders_under_time_travel(seeded, invocation):
    """A stored date range either applies or is warned about, and never crashes a command."""
    stored = ((NOW - timedelta(days=120)).timestamp(), NOW.timestamp())
    ctx = asyncio.run(invoke(invocation, stored=stored))

    assert ctx.sent, f"{invocation} sent nothing under a stored date range"


@pytest.mark.parametrize("invocation", INVOCATIONS)
def test_a_command_renders_under_a_universe(seeded, invocation):
    """A stored universe either applies or is warned about, and never crashes a command."""
    # The seed holds three Spanish quotes, so an empty result is the right answer, not a failure.
    try:
        ctx = asyncio.run(invoke(invocation, universe="es"))
    except CommandError:
        return

    assert ctx.sent, f"{invocation} sent nothing under a stored universe"


@pytest.mark.parametrize("invocation", RAW_PP_REFUSED)
def test_raw_pp_output_is_refused_without_gg_plus(seeded, invocation):
    """A command whose whole output is raw pp refuses a non-subscriber."""
    with pytest.raises(NotSubscribed):
        asyncio.run(invoke(invocation, gg_plus=False))


@pytest.mark.parametrize("invocation", RAW_PP_SUBSTITUTED)
def test_raw_pp_fields_still_render_without_gg_plus(seeded, invocation):
    """A command showing raw pp as one field still renders for a non-subscriber."""
    ctx = asyncio.run(invoke(invocation, gg_plus=False))

    assert ctx.sent, f"{invocation} sent nothing without GG+"


@pytest.mark.parametrize("invocation", GG_PLUS_REFUSED)
def test_a_gg_plus_command_is_refused_without_gg_plus(seeded, invocation):
    """A GG+ command refuses a non-subscriber."""
    with pytest.raises(NotSubscribed):
        asyncio.run(invoke(invocation, gg_plus=False))


def test_daily_narrows_comparegraph_without_a_warning(seeded):
    """`daily` reaches -comparegraph as a filter, not as an unsupported quote ID."""
    ctx = asyncio.run(invoke("-comparegraph eiko keegan daily"))

    assert not any("no effect" in (sent.get("content") or "") for sent in ctx.sent)
    assert "Daily Quotes" in ctx.sent[-1]["embed"].title


def test_a_length_range_narrows_comparegraph_without_a_warning(seeded):
    """A `c` length range reaches -comparegraph as a flag and names itself in the title."""
    ctx = asyncio.run(invoke("-comparegraph eiko keegan <500c"))

    assert not any("no effect" in (sent.get("content") or "") for sent in ctx.sent)
    assert "<500 chars" in ctx.sent[-1]["embed"].title


def logged_race_number(longest: bool) -> int:
    """Return the seeded user's race with the longest or shortest keystroke log."""
    return typegg_db.reader.execute(f"""
        SELECT r.raceNumber FROM races r
        JOIN keystroke_data k ON k.raceId = r.raceId
        WHERE r.userId = ?
        ORDER BY LENGTH(k.keystrokeData) {"DESC" if longest else "ASC"}
        LIMIT 1
    """, [seed_data.USER_ID]).fetchone()[0]


def test_keystrokelog_refuses_another_users_race(seeded):
    """A raw keystroke log is shown only to its racer."""
    with pytest.raises(BotError) as error:
        asyncio.run(invoke(f"-keystrokelog {seed_data.RIVAL_ID}"))

    assert error.value.title == "Privacy Error"


def test_an_admin_can_view_another_users_keystroke_log(seeded):
    """An admin bypasses the privacy check."""
    ctx = asyncio.run(invoke(f"-keystrokelog {seed_data.RIVAL_ID}", admin=True))

    assert ctx.sent[-1]["content"].startswith("**Keystroke Log")


def test_a_short_keystroke_log_is_a_code_block(seeded):
    """A log that fits one message lands in a plain code block with no embed or attachment."""
    ctx = asyncio.run(invoke(f"-keystrokelog {logged_race_number(longest=False)}"))

    assert "```json" in ctx.sent[-1]["content"]
    assert not any("file" in sent or "embed" in sent for sent in ctx.sent)


def test_a_long_keystroke_log_is_attached_as_a_file(seeded):
    """A log too long for one message arrives as a file under the header."""
    number = logged_race_number(longest=True)
    ctx = asyncio.run(invoke(f"-keystrokelog {number}"))

    assert "```" not in ctx.sent[-1]["content"]
    assert ctx.sent[-1]["file"].filename == f"{seed_data.USER_ID}_{number}.json"


def comparison_line(ctx: FakeContext, label: str) -> str:
    """Return the description line a race comparison wrote under one label."""
    description = ctx.sent[-1]["embed"].description
    return next(line for line in description.splitlines() if line.startswith(f"**{label}:**"))


def test_numbers_after_a_quote_id_are_attempts_on_that_quote(seeded):
    """Attempt N is the user's Nth race on the quote, as the site's replay history counts it."""
    quote_races = sorted(
        (race for race in RACES if race["userId"] == seed_data.USER_ID and race["quoteId"] == "q1"),
        key=lambda race: race["timestamp"],
    )
    ctx = asyncio.run(invoke("-rc q1 2 -1"))

    assert f"{quote_races[1]["wpm"]:,.2f}" in comparison_line(ctx, "Attempt #2")
    assert f"{quote_races[-2]["wpm"]:,.2f}" in comparison_line(ctx, f"Attempt #{len(quote_races) - 1}")


def test_one_race_number_is_compared_with_the_best(seeded):
    """A single number overlays that race on the user's best race on its quote."""
    quote_races = [race for race in RACES if race["userId"] == seed_data.USER_ID and race["quoteId"] == "q1"]
    best = max(quote_races, key=lambda race: race["wpm"])
    number = next(race["raceNumber"] for race in quote_races if race is not best)
    ctx = asyncio.run(invoke(f"-rc {number}"))

    assert f"{best["wpm"]:,.2f}" in comparison_line(ctx, "Best")
    assert comparison_line(ctx, f"Race #{number:,}")


def test_race_numbers_on_different_quotes_are_refused(seeded):
    """Races picked by account number must share a quote to overlay."""
    with pytest.raises(BotError) as error:
        asyncio.run(invoke("-rc 1 2"))

    assert error.value.title == "Different Quotes"


def test_racecompare_keeps_another_users_races_private(seeded):
    """Picked races may be non-PB solo races, which only their racer can see."""
    with pytest.raises(BotError) as error:
        asyncio.run(invoke(f"-rc {seed_data.RIVAL_ID} 60 120"))

    assert error.value.title == "Privacy Error"


def test_an_admin_can_compare_another_users_races(seeded):
    """An admin bypasses the privacy check on picked races."""
    ctx = asyncio.run(invoke(f"-rc {seed_data.RIVAL_ID} 60 120", admin=True))

    assert ctx.sent[-1]["embed"].title.startswith("Race Comparison")


def rival_race_number(kind: str) -> int:
    """Return one of the rival's races that is a hidden solo race, their best on a quote, or a match."""
    public_best = """(
        SELECT b.raceId FROM races b
        WHERE b.userId = r.userId AND b.quoteId = r.quoteId AND b.raceNumber IS NOT NULL
        ORDER BY b.pp DESC, b.wpm DESC, b.raceId ASC
        LIMIT 1
    )"""
    condition = {
        "hidden": f"r.matchId IS NULL AND r.raceId != {public_best}",
        "best": f"r.matchId IS NULL AND r.raceId = {public_best}",
        "match": "r.matchId IS NOT NULL",
    }[kind]

    return typegg_db.reader.execute(f"""
        SELECT r.raceNumber FROM races r
        JOIN keystroke_data k ON k.raceId = r.raceId
        WHERE r.userId = ? AND r.raceNumber IS NOT NULL AND {condition}
        LIMIT 1
    """, [seed_data.RIVAL_ID]).fetchone()[0]


def test_racegraph_keeps_another_users_other_solo_races_private(seeded):
    """A solo race that is not the racer's best on its quote is shown only to them."""
    with pytest.raises(BotError) as error:
        asyncio.run(invoke(f"-racegraph {seed_data.RIVAL_ID} {rival_race_number("hidden")}"))

    assert error.value.title == "Privacy Error"


@pytest.mark.parametrize("kind", ["best", "match"])
def test_racegraph_shows_another_users_public_races(seeded, kind):
    """Another user's best race on a quote and their matches are public."""
    ctx = asyncio.run(invoke(f"-racegraph {seed_data.RIVAL_ID} {rival_race_number(kind)}"))

    assert ctx.sent


def test_an_admin_can_graph_another_users_private_race(seeded):
    """An admin bypasses the privacy check on race graphs."""
    ctx = asyncio.run(invoke(f"-racegraph {seed_data.RIVAL_ID} {rival_race_number("hidden")}", admin=True))

    assert ctx.sent


def sum_of_best_speed(invocation: str) -> float:
    """Return the Speed line a sum of best invocation renders."""
    description = asyncio.run(invoke(invocation)).sent[-1]["embed"].description
    line = next(line for line in description.split("\n") if line.startswith("**Speed:**"))
    return float(line.split()[1].replace(",", ""))


def test_raw_sum_of_best_builds_from_raw_segments(seeded):
    """Raw times drop mistake recovery, so the seeded raw sum of best comes out faster."""
    assert sum_of_best_speed("-sumofbest raw") > sum_of_best_speed("-sumofbest")


def sent_warnings(ctx: FakeContext) -> list[str]:
    """Return the subtext warnings a command sent before its embed."""
    return [message["content"] for message in ctx.sent if (message.get("content") or "").startswith("-# ")]


def test_a_foreign_universe_averages_solo_races(seeded):
    """Quickplay serves only English quotes, so a non-English universe averages solo races instead."""
    ctx = asyncio.run(invoke("-average", universe="es"))

    assert ctx.flags.gamemode == "solo"
    assert "Spanish" in ctx.sent[-1]["embed"].title


@pytest.mark.parametrize("invocation", ["-average quickplay", "-positionstats"])
def test_a_multiplayer_command_drops_a_foreign_universe(seeded, invocation):
    """Multiplayer runs in English, and says so rather than finding no races."""
    ctx = asyncio.run(invoke(invocation, universe="es"))

    assert ctx.flags.language is None
    assert "-# :warning: your universe has no effect on multiplayer races" in sent_warnings(ctx)


def universe_race_numbers(seeded, language: str) -> list[int]:
    """Return the seeded user's race numbers on quotes in one language, latest first."""
    return [row[0] for row in seeded.typegg.execute("""
        SELECT r.raceNumber FROM races r JOIN quotes q ON q.quoteId = r.quoteId
        WHERE r.userId = ? AND q.language = ? AND r.raceNumber IS NOT NULL
        ORDER BY r.raceNumber DESC
    """, [seed_data.USER_ID, language])]


@pytest.mark.parametrize("invocation, back", [("-r", 0), ("-r -1", 1)])
def test_a_universe_picks_the_latest_race_within_it(seeded, invocation, back):
    """Latest and negative race numbers count through the universe's races alone."""
    ctx = asyncio.run(invoke(invocation, universe="es"))

    assert ctx.sent[-1]["embed"].title == f"Race Graph - Race #{universe_race_numbers(seeded, "Spanish")[back]:,}"


def test_a_positive_race_number_ignores_the_universe(seeded):
    """A positive number names one race on the whole account."""
    number = next(n for n in range(1, 100) if n not in universe_race_numbers(seeded, "Spanish"))
    ctx = asyncio.run(invoke(f"-r {number}", universe="es"))

    assert ctx.sent[-1]["embed"].title == f"Race Graph - Race #{number:,}"


def test_a_quote_outside_the_universe_still_finds_its_races(seeded):
    """The universe only picks the latest race, so a quote from another language keeps its races."""
    ctx = asyncio.run(invoke("-segments q1", universe="es"))

    assert "embed" in ctx.sent[-1] and not sent_warnings(ctx)


@pytest.mark.parametrize("invocation", ["-timetravel", "-lastonline"])
def test_a_command_with_no_use_for_the_settings_stays_quiet(seeded, invocation):
    """Commands that set or ignore the stored settings do not warn about them."""
    stored = ((NOW - timedelta(days=120)).timestamp(), NOW.timestamp())
    ctx = asyncio.run(invoke(invocation, stored=stored, universe="es"))

    assert not [warning for warning in sent_warnings(ctx) if ":warning:" in warning]


def test_a_histogram_without_typos_notes_its_empty_timing_pages(seeded, monkeypatch):
    """A clean race times its typos as 0, which once left the quartiles nothing to read."""
    from commands.graphs import histogram

    quote_bests = histogram.get_quote_bests

    def clean_quote_bests(*args, **kwargs) -> list[dict]:
        """Return the seeded quote bests with every typo timing zeroed."""
        return [dict(race, errorReactionTime=0, errorRecoveryTime=0) for race in quote_bests(*args, **kwargs)]

    monkeypatch.setattr(histogram, "get_quote_bests", clean_quote_bests)
    ctx = asyncio.run(invoke("-histogram react"))

    assert "No races with a typo" in ctx.sent[-1]["embed"].description


def test_a_raw_histogram_hides_its_pp_page_without_gg_plus(seeded):
    """Only the typed metric is gated, so the pp button must not carry raw pp past it."""
    ctx = asyncio.run(invoke("-histogram wpm raw", gg_plus=False))

    assert "pp" not in [button.label for button in ctx.sent[-1]["view"].children]


def test_raw_race_history_titles_raw_once(seeded):
    """The flag title already carries Raw, so the page title must not add its own."""
    ctx = asyncio.run(invoke("-racehistory raw"))

    assert ctx.sent[-1]["embed"].title.count("Raw") == 1


def test_an_error_page_names_the_universe_that_emptied_it(seeded):
    """A stored universe is easy to forget, so an empty result says which one ran."""
    ctx = asyncio.run(invoke("-simp", universe="de"))

    assert ctx.sent[-1]["content"] == "-# :earth_africa: German universe"


@pytest.mark.parametrize("wrap", [True, False])
def test_only_an_invoked_error_names_the_range_and_universe(seeded, wrap):
    """An error raised before cog_before_invoke still holds flags the command would have cleared."""
    ctx = FakeContext("-average", build_user(), bot=None)
    stored = ((NOW - timedelta(days=1)).timestamp(), NOW.timestamp())
    ctx.flags.date_range = resolve_date_range(ctx.flags, ctx.user["timezone"], stored)
    ctx.flags.language = resolve_universe(ctx.flags, "es")
    error = NoRacesFiltered(seed_data.USER_ID)

    asyncio.run(ErrorHandler(None).on_command_error(ctx, CommandInvokeError(error) if wrap else error))
    content = ctx.sent[-1]["content"]

    if wrap:
        assert content.startswith("-# <:galaxy:") and content.endswith("\n-# :earth_africa: Spanish universe")
    else:
        assert content is None


def test_average_shows_a_speed_spread_from_two_races(seeded):
    """Speed carries a ± spread, which a single race is too few to have."""
    spread = asyncio.run(invoke("-average")).sent[-1]["embed"].fields[0].value
    single = asyncio.run(invoke("-average 1")).sent[-1]["embed"].fields[0].value

    assert "±" in spread
    assert "±" not in single


def test_the_seed_is_isolated_from_the_real_database(seeded):
    """The suite must never read the 3 GB production database."""
    assert isinstance(typegg_db.reader, sqlite3.Connection)
    assert typegg_db.reader.execute("SELECT COUNT(*) FROM races").fetchone()[0] == (
        seed_data.RACE_COUNT + seed_data.RIVAL_RACE_COUNT
    )
