from typing import Optional

from discord.ext import commands

from api.users import get_profile
from database.bot.users import get_user
from utils.errors import UserBanned, MissingUsername, ProfileNotFound, NoRaces


class Command(commands.Cog):
    """Base command class providing common command utilities."""

    def __init__(self, bot):
        self.bot = bot

        @bot.check
        async def set_user(ctx: commands.Context):
            """Attach a user to the context and block banned users."""
            if not hasattr(ctx, "user"):
                ctx.user = get_user(str(ctx.author.id))
            if ctx.user["isBanned"]:
                raise UserBanned("Banned user attempted to use a command")
            return True

    def get_username(self, ctx: commands.Context, username: str):
        """Resolve 'me' to the current user's ID or return the provided username."""
        if username == "me":
            return ctx.user["userId"]
        return username

    def get_usernames(self, ctx: commands.Context, username1: str, username2: str):
        """Resolves 'me' to current user's ID and returns both usernames"""
        if username2 == "me":
            username1, username2 = username2, username1

        return self.get_username(ctx, username1), self.get_username(ctx, username2)

    async def get_profile(self, ctx: commands.Context, username: str, races_required: Optional[bool] = False):
        """Fetch a user's profile, raising exceptions if missing."""
        username = self.get_username(ctx, username)
        if username is None:
            raise MissingUsername

        profile = await get_profile(username)
        if not profile:
            raise ProfileNotFound(username)

        if races_required and profile["stats"]["races"] == 0:
            raise NoRaces(username)

        return profile

    async def import_user(self, ctx: commands.Context, profile: dict):
        from commands.account.download import run as download
        await download(ctx, profile)
