import asyncio
from typing import Optional, NamedTuple
from urllib.parse import unquote

from discord import Forbidden
from discord.ext import commands

from api.quotes import get_quote as get_quote_api
from api.users import get_profile, get_races
from bot_setup import BotContext
from config import SITE_URL, STATS_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote, get_recent_quote
from database.bot.users import update_warning, update_gg_plus_status, get_user_by_user_id
from database.typegg.daily_quotes import get_daily_quote_id
from database.typegg.quotes import get_quote as get_quote_db
from database.typegg.races import get_latest_race
from utils.errors import NoRaces, NotSubscribed, InvalidNumber, NoRacesFiltered, MissingUsername
from utils.flags import Flags
from utils.messages import privacy_warning, command_milestone
from utils.strings import parse_number, get_argument


class ParseResult(NamedTuple):
    remaining: list
    username: str | None
    argument: str | None


class Command(commands.Cog):
    """Base command class providing common command utilities."""

    supported_flags: set[str] = set()

    def __init__(self, bot):
        self.bot = bot

    async def cog_before_invoke(self, ctx: BotContext):
        if hasattr(self, "ignore_flags"):
            return

        explicit = getattr(ctx, "explicit_flags", {})
        unsupported = {name: arg for name, arg in explicit.items() if name not in self.supported_flags}

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

    async def celebrate_milestone(self, ctx: BotContext, milestone: int):
        channel = self.bot.get_channel(STATS_CHANNEL_ID)
        if channel:
            await channel.send(embed=command_milestone(ctx.author.id, milestone))

    def _get_db_user_gg_plus(self, user_id: str):
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
    ):
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

    def get_username(self, ctx: BotContext, username: Optional[str]):
        """Resolve None or 'me' to the current user's ID, or return the provided username."""
        if username is None or username == "me":
            if ctx.user["userId"] is None:
                raise MissingUsername
            return ctx.user["userId"]
        return username

    def get_usernames(self, ctx: BotContext, username1: Optional[str], username2: Optional[str]):
        """Resolves None/'me' to current user's ID and returns both usernames."""
        if username2 is None or username2 == "me":
            username1, username2 = username2, username1

        username1 = self.get_username(ctx, username1)
        username2 = self.get_username(ctx, username2)

        return username1, username2

    async def get_profile(
        self,
        ctx: BotContext,
        username: Optional[str] = None,
        races_required: Optional[bool] = True,
        auto_import=True,
    ):
        """Fetch a user's profile, and optionally imports their races."""
        username = self.get_username(ctx, username)

        profile = await get_profile(username)

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

    async def import_user(self, ctx: BotContext, profile: dict):
        from commands.account.download import run as download
        await download(ctx, profile)

    async def await_confirmation(self, ctx: BotContext, confirm_message="confirm", timeout=10):
        """Waits for the user to send a specific confirmation message."""

        def check(message):
            return (
                message.author == ctx.author
                and message.channel == ctx.channel
                and message.content.lower() == confirm_message.lower()
            )

        try:
            await self.bot.wait_for("message", timeout=timeout, check=check)
            return True
        except asyncio.TimeoutError:
            return False

    async def send_privacy_warning(self, ctx: BotContext):
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
        quote_id: Optional[str] = None,
        user_id: Optional[str] = None,
        from_api: Optional[bool] = False,
    ):
        """Fetches a quote from database or API, optionally pass a user ID to take their latest quote ID."""
        if quote_id is None and user_id is not None:
            latest_race = get_latest_race(user_id)
            quote_id = latest_race["quoteId"]
        elif quote_id.startswith(f"{SITE_URL}/solo/"):
            quote_id = quote_id.split("/")[-1]
        elif quote_id == "^":
            quote_id = get_recent_quote(ctx.channel.id)
        elif quote_id == "daily":
            quote_id = get_daily_quote_id()

        quote_id = unquote(quote_id)

        if from_api:
            quote = await get_quote_api(quote_id)
        else:
            quote = get_quote_db(quote_id)

        set_recent_quote(ctx.channel.id, quote_id)
        return quote

    async def get_race_number(self, profile, race_number):
        total_races = (await get_races(profile["userId"], per_page=1))["races"][0]["raceNumber"]
        if total_races is None:
            total_races = profile["stats"]["races"]

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

    def check_gg_plus(self, ctx: BotContext, feature: str = None):
        if not ctx.user["isGgPlus"]:
            if feature:
                raise NotSubscribed(feature)
            raise NotSubscribed
        return
