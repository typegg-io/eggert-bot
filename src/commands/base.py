import asyncio
from typing import Optional
from urllib.parse import unquote

from discord import Forbidden
from discord.ext import commands

from api.quotes import get_quote as get_quote_api
from api.users import get_profile, get_races
from config import SITE_URL, STATS_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote, get_recent_quote
from database.bot.users import update_warning
from database.typegg.daily_quotes import get_daily_quote_id
from database.typegg.quotes import get_quote
from database.typegg.races import get_latest_race
from utils.errors import MissingUsername, NoRaces, NotSubscribed, InvalidNumber
from utils.messages import privacy_warning, command_milestone
from utils.strings import parse_number


class Command(commands.Cog):
    """Base command class providing common command utilities."""

    def __init__(self, bot):
        self.bot = bot

    async def celebrate_milestone(self, ctx: commands.Context, milestone: int):
        channel = self.bot.get_channel(STATS_CHANNEL_ID)
        if channel:
            await channel.send(embed=command_milestone(ctx.author.id, milestone))

    def get_username(self, ctx: commands.Context, username: str):
        """Resolve 'me' to the current user's ID or return the provided username."""
        if username == "me":
            return ctx.user["userId"]
        return username

    def get_usernames(self, ctx: commands.Context, username1: str, username2: str):
        """Resolves 'me' to current user's ID and returns both usernames"""
        if username2 == "me":
            username1, username2 = username2, username1

        username1 = self.get_username(ctx, username1)
        username2 = self.get_username(ctx, username2)

        return username1, username2

    async def get_profile(self, ctx: commands.Context, username: str, races_required: Optional[bool] = False):
        """Fetch a user's profile, raising exceptions if missing."""
        username = self.get_username(ctx, username)
        if username is None:
            raise MissingUsername

        profile = await get_profile(username)
        if races_required and profile["stats"]["races"] == 0:
            raise NoRaces(username)

        return profile

    async def import_user(self, ctx: commands.Context, profile: dict):
        from commands.account.download import run as download
        await download(ctx, profile)

    async def await_confirmation(self, ctx, confirm_message="confirm", timeout=10):
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

    async def send_privacy_warning(self, ctx: commands.Context):
        """Sends out a one-time privacy warning DM."""
        embed = privacy_warning()
        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            await ctx.send(embed=embed)
        update_warning(ctx.author.id)

    async def get_quote(
        self,
        ctx: commands.Context,
        quote_id: Optional[str] = None,
        user_id: Optional[str] = None,
        from_api: Optional[bool] = False,  # this won't be needed once the web server receives quote udpates
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
            quote = get_quote(quote_id)

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

        return race_number

    def check_gg_plus(self, ctx, feature: str = None):
        if not ctx.user["isGgPlus"]:
            if feature:
                raise NotSubscribed(feature)
            raise NotSubscribed
        return
