import asyncio
from typing import Optional
from urllib.parse import unquote

from discord import Forbidden
from discord.ext import commands

from api.quotes import get_quote as get_quote_api
from api.users import get_profile
from config import DAILY_QUOTE_CHANNEL_ID, SITE_URL, BOT_PREFIX, STAGING, STATS_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote, get_recent_quote
from database.bot.users import get_user, update_warning, get_user_ids, get_all_command_usage, update_commands
from database.typegg.quotes import get_quote
from database.typegg.races import get_latest_race
from utils.errors import UserBanned, MissingUsername, NoRaces, DailyQuoteChannel, NotSubscribed
from utils.logging import get_log_message, log
from utils.messages import privacy_warning, welcome_message, command_milestone
from utils.strings import parse_number, get_argument

FLAGS = {"raw", "solo", "multiplayer", "unranked", "any"}
users = get_user_ids()
total_commands = sum(get_all_command_usage().values())


class Command(commands.Cog):
    """Base command class providing common command utilities."""

    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def set_user(ctx: commands.Context):
            """Attach a user to the context and block banned users."""
            ctx.flags = ctx.message.flags
            if (
                ctx.channel.id == DAILY_QUOTE_CHANNEL_ID
                and str(ctx.command) not in ["dailyleaderboard", "dailystats", "dailygraph"]
            ):
                raise DailyQuoteChannel
            if not hasattr(ctx, "user"):
                ctx.user = get_user(str(ctx.author.id))
            if ctx.user["isBanned"]:
                raise UserBanned("Banned user attempted to use a command")
            return True

        @bot.event
        async def on_message(message):
            """Global message handler."""

            if not message.content.startswith(BOT_PREFIX) or message.author.bot:
                return

            # Logging
            if not STAGING:
                log_message = get_log_message(message)
                log(log_message)

                # New users
                if message.author.id not in users:
                    users.append(message.author.id)
                    if not message.content.startswith(("-link", "-verify")):
                        return await message.reply(content=welcome_message)

            # Parsing flags
            content = message.content
            invoke, raw_args = content.split()[0], content.split()[1:]

            flags = {}
            regular_args = []

            for arg in raw_args:
                if arg.startswith("-"):
                    flag = get_argument(FLAGS, arg.lstrip("-"), _raise=False)

                    if not flag:
                        regular_args.append(arg)
                        continue

                    match flag:
                        case "raw":
                            flags["metric"] = flag
                        case "solo" | "multiplayer":
                            flags["gamemode"] = flag
                        case "unranked" | "any":
                            flags["status"] = flag
                else:
                    regular_args.append(arg)

            message.flags = flags
            message.content = f"{invoke} " + " ".join(regular_args)

            await bot.process_commands(message)

        @bot.event
        async def on_command_completion(ctx: commands.Context):
            global total_commands

            command_origin = "server" if ctx.guild else "dm"
            update_commands(ctx.author.id, ctx.command.name, command_origin)

            total_commands += 1
            if total_commands % 50_000 == 0:
                await self.celebrate_milestone(ctx, total_commands)

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

        quote_id = unquote(quote_id)

        if from_api:
            quote = await get_quote_api(quote_id)
        else:
            quote = get_quote(quote_id)

        set_recent_quote(ctx.channel.id, quote_id)
        return quote

    def get_race_number(self, profile, race_number):
        if race_number is None:
            race_number = profile["stats"]["races"]
        else:
            race_number = parse_number(race_number)

        if race_number < 1:
            race_number = profile["stats"]["races"] + race_number

        return race_number

    def check_gg_plus(self, ctx, feature: str = None):
        if not ctx.user["isGgPlus"]:
            if feature:
                raise NotSubscribed(feature)
            raise NotSubscribed
        return
