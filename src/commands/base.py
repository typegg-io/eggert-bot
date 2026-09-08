"""The base class and shared helpers every command file builds on."""

from typing import NamedTuple
from urllib.parse import unquote

from discord import Embed, Forbidden, Message
from discord.ext import commands

from api.quotes import get_quote as get_quote_api
from api.users import get_profile
from config import DAILY_QUOTE_CHANNEL_ID, STATS_CHANNEL_ID
from context import BotContext
from database.bot.recent_quotes import get_recent_quote, set_recent_quote
from database.bot.users import get_user_by_user_id, update_gg_plus_status, update_warning
from database.typegg.daily_quotes import get_daily_quote_id
from database.typegg.quotes import get_quote as get_quote_db
from database.typegg.races import get_latest_race
from services.importer import get_total_races, run as import_races
from utils.colors import ERROR
from utils.errors import (
    DailyQuoteChannel,
    InvalidNumber,
    MissingArguments,
    MissingUsername,
    NoRaces,
    NoRacesFiltered,
    NotSubscribed,
)
from utils.flags import Flags, universe_code
from utils.messages import command_milestone, privacy_warning
from utils.schemas import Profile
from utils.strings import get_argument, parse_number
from utils.urls import parse_solo_url


class ParseResult(NamedTuple):
    """The leftover args, username and argument that `extract_params` pulls apart."""

    remaining: list
    username: str | None
    argument: str | None


def enforce_daily_quote(ctx: BotContext, quote_id: str) -> None:
    """In the daily quote channel, only allow commands acting on the current daily quote."""
    if ctx.channel.id == DAILY_QUOTE_CHANNEL_ID and quote_id != get_daily_quote_id():
        raise DailyQuoteChannel


async def take_universe(ctx: BotContext) -> str | None:
    """Return the universe code to send, warning and clearing a language that has no universe."""
    if not ctx.flags.language:
        return None

    code = universe_code(ctx.flags)
    if not code:
        await ctx.send(f"-# :warning: {ctx.flags.language.name} has no universe of its own")
        ctx.flags.language = None

    return code


class Command(commands.Cog):
    """Base command class providing common command utilities."""

    supported_flags: set[str] = set()

    def __init__(self, bot) -> None:
        """Store the bot instance the cog was loaded onto."""
        self.bot = bot

    async def cog_before_invoke(self, ctx: BotContext) -> None:
        """Warn about flags this command does not support, then reset them to their defaults."""
        explicit = getattr(ctx, "explicit_flags", {})
        unranged = "date_range" not in self.supported_flags
        stored_range = bool(ctx.flags.date_range) and "date_range" not in explicit
        universeless = "language" not in self.supported_flags
        stored_universe = bool(ctx.flags.language) and "language" not in explicit

        # A stored range applies with nothing typed, so ignore_flags commands still have to clear it.
        if unranged:
            ctx.flags.date_range = None

        if universeless:
            ctx.flags.language = None

        if hasattr(self, "ignore_flags"):
            return

        unsupported = {name: arg for name, arg in explicit.items() if name not in self.supported_flags}

        # A second date on a command that takes one is redundant, not wrong, so it passes in silence.
        if "date" in self.supported_flags and not ctx.flags.period:
            unsupported.pop("date_range", None)

        if unsupported:
            args = list(unsupported.values())
            if len(args) == 1:
                flag_str = f"`{args[0]}`"
            else:
                flag_str = ", ".join(f"`{a}`" for a in args[:-1]) + f" and `{args[-1]}`"
            has_have = "has" if len(args) == 1 else "have"
            await ctx.send(f"-# :warning: {flag_str} {has_have} no effect on this command")

            defaults = Flags()
            for name in unsupported:
                if hasattr(ctx.flags, name):
                    setattr(ctx.flags, name, getattr(defaults, name))

        if unranged and stored_range:
            await ctx.send("-# :warning: time travel has no effect on this command")

        if universeless and stored_universe:
            await ctx.send("-# :warning: your universe has no effect on this command")

    async def celebrate_milestone(self, ctx: BotContext, milestone: int) -> None:
        """Announce a user's command count milestone in the stats channel."""
        channel = self.bot.get_channel(STATS_CHANNEL_ID)
        if channel:
            await channel.send(embed=command_milestone(ctx.author.id, milestone))

    def _get_db_user_gg_plus(self, user_id: str) -> bool | None:
        """Fetch the GG+ status from the database (synchronous)."""
        user = get_user_by_user_id(user_id)
        return user["isGgPlus"] if user else None

    def extract_params(self, args: tuple, extract: list) -> ParseResult:
        """Extract a username and argument given args and argument keys."""
        remaining = []
        argument = None

        for arg in args:
            if argument is None and (a := get_argument(extract, arg, _raise=False)):
                argument = a
            else:
                remaining.append(arg)

        username = remaining[0] if remaining else None
        return ParseResult(remaining, username, argument)

    async def get_profiles(
        self,
        ctx: BotContext,
        args: list | tuple,
        max_users: int = 5,
        auto_import: bool = True
    ) -> list[Profile]:
        """Deduplicate & clamp a list of usernames, then fetch & import each profile."""
        usernames = list(dict.fromkeys(args))
        usernames = usernames[:max_users] or [ctx.user["userId"]]
        profiles = []
        seen = set()

        for username in usernames:
            profile = await self.get_profile(ctx, username, auto_import=False)

            if profile["userId"] in seen:
                continue

            if auto_import:
                await self.import_user(ctx, profile)

            seen.add(profile["userId"])
            profiles.append(profile)

        return profiles

    def get_username(self, ctx: BotContext, username: str | None) -> str:
        """Resolve None or 'me' to the current user's ID, or return the provided username."""
        if username is None or username == "me":
            if ctx.user["userId"] is None:
                raise MissingUsername
            return ctx.user["userId"]
        return username

    def get_usernames(self, ctx: BotContext, username1: str | None, username2: str | None) -> tuple[str, str]:
        """Resolves None/'me' to current user's ID and returns both usernames."""
        if username2 is None or username2 == "me":
            username1, username2 = username2, username1

        username1 = self.get_username(ctx, username1)
        username2 = self.get_username(ctx, username2)

        return username1, username2

    async def get_profile(
        self,
        ctx: BotContext,
        username: str | None = None,
        races_required: bool | None = True,
        auto_import: bool = True,
    ) -> Profile:
        """Fetch a user's profile, and optionally imports their races."""
        username = self.get_username(ctx, username)

        profile = await get_profile(username, universe=universe_code(ctx.flags))

        # Sync GG+ status
        api_gg_plus = profile.get("isGgPlus", False)
        db_user = self._get_db_user_gg_plus(profile["userId"])
        if db_user is not None and db_user != api_gg_plus:
            update_gg_plus_status(profile["userId"], api_gg_plus)

        if races_required:
            if ctx.flags.gamemode == "quickplay":
                if profile["stats"]["quickplayRaces"] == 0:
                    raise NoRacesFiltered(username)
            else:
                if profile["stats"]["races"] == 0:
                    raise NoRaces(username)

        if auto_import:
            await self.import_user(ctx, profile)

        return profile

    async def import_user(self, ctx: BotContext, profile: Profile) -> None:
        """Import the profile's new races, rendering progress into the command's channel."""
        await import_races(ctx, profile, auto_import=True)

    async def await_confirmation(
        self,
        ctx: BotContext,
        confirm_message: str = "confirm",
        timeout: int = 10,
        prompt_message: Message | None = None,
    ) -> bool:
        """Waits for the user to send a specific confirmation message."""

        def check(message) -> bool:
            """Return whether this message is the confirmation the command is waiting on."""
            return (
                message.author == ctx.author
                and message.channel == ctx.channel
                and message.content.lower() == confirm_message.lower()
            )

        try:
            await self.bot.wait_for("message", timeout=timeout, check=check)
            return True
        except TimeoutError:
            if prompt_message is not None:
                await prompt_message.edit(
                    embed=Embed(
                        title="Confirmation Expired",
                        description="Please run the command again.",
                        color=ERROR,
                    ),
                    view=None,
                )
            return False

    async def send_privacy_warning(self, ctx: BotContext) -> None:
        """Sends out a one-time privacy warning DM."""
        embed = privacy_warning()
        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            await ctx.send(embed=embed)
        update_warning(ctx.author.id)

    async def get_quote(
        self,
        ctx: BotContext,
        quote_id: str | None = None,
        user_id: str | None = None,
        from_api: bool | None = False,
    ) -> dict:
        """Fetches a quote from database or API, optionally pass a user ID to take their latest quote ID."""
        if quote_id is None and user_id is not None:
            latest_race = get_latest_race(user_id)
            quote_id = latest_race["quoteId"]
        elif (solo_quote_id := parse_solo_url(quote_id)) is not None:
            quote_id = solo_quote_id
        elif quote_id == "^":
            quote_id = get_recent_quote(ctx.channel.id)
            if quote_id is None:
                raise MissingArguments
        elif quote_id == "daily":
            quote_id = get_daily_quote_id()

        quote_id = unquote(quote_id)

        if from_api:
            quote = await get_quote_api(quote_id)
        else:
            quote = get_quote_db(quote_id)

        set_recent_quote(ctx.channel.id, quote_id)
        return quote

    async def get_race_number(self, profile, race_number) -> int:
        """Resolve a race number, defaulting to the latest and counting backwards when negative."""
        # Fetch the API's true latest race number, fall back to the latest stored race
        total_races = await get_total_races(profile["userId"])
        if not total_races:
            latest_race = get_latest_race(profile["userId"])
            total_races = latest_race["raceNumber"] if latest_race else profile["stats"]["races"]

        if race_number is None:
            race_number = total_races
        else:
            try:
                race_number = parse_number(race_number)
            except ValueError:
                raise InvalidNumber
            if race_number < 1:
                race_number = total_races + race_number

        return int(race_number)

    def check_gg_plus(self, ctx: BotContext, feature: str = None) -> None:
        """Raise unless the invoking user has a GG+ subscription."""
        if not ctx.user["isGgPlus"]:
            if feature:
                raise NotSubscribed(feature)
            raise NotSubscribed
        return
