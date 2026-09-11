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
from discord.ext.commands import CommandError

from bot_setup import parse_flags
from commands.base import Command
from database.bot import db as bot_db
from database.typegg import db as typegg_db
from utils.colors import DEFAULT_THEME
from utils.dates import resolve_date_range
from utils.errors import NotSubscribed
from utils.flags import apply_universe_status, resolve_universe

matplotlib.use("Agg")

pytestmark = pytest.mark.slow

NOW = datetime.now(UTC)

# One invocation per line, written the way a user types it.
INVOCATIONS = [
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
    "-histogram",
    "-leaderboard qo 100",
    "-improvement",
    "-improvement acc",
    "-simp acc",
    "-keystrokes",
    "-lastonline",
    "-lengthgraph",
    "-lengthgraph raw",
    "-linegraph",
    "-linegraph nwpm",
    "-linegraph level",
    "-linegraph playtime",
    "-longestaverage 100",
    "-matchgraph",
    "-month",
    "-pplength",
    "-pplength raw",
    "-quote q1",
    "-quoteleaderboard q1",
    "-quotesover 100",
    "-quotestrength",
    "-quotestrength raw",
    "-racecompare 599 600",
    "-racegraph",
    "-racehistory",
    "-racehistory raw",
    "-races",
    "-segments",
    "-stats",
    "-sumofbest",
    "-timetravel",
    "-toptens",
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
    "-racegraph",
    "-racehistory raw",
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
    "translate": "calls a translation API",
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
            "quotesTyped": len(seed_data.QUOTE_FIXTURES),
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
) -> FakeContext:
    """Run one invocation end to end and return the context it sent through."""
    name = invocation.split()[0].lstrip("-")
    cog_class, command = find_command(name)
    user = build_user()
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


def test_the_seed_is_isolated_from_the_real_database(seeded):
    """The suite must never read the 3 GB production database."""
    assert isinstance(typegg_db.reader, sqlite3.Connection)
    assert typegg_db.reader.execute("SELECT COUNT(*) FROM races").fetchone()[0] == (
        seed_data.RACE_COUNT + seed_data.RIVAL_RACE_COUNT
    )
