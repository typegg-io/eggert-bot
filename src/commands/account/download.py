from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from services.importer import run

info = CommandInfo(
    name="download",
    aliases=["import", "dl", "gd", "i"],
    description="Imports a user's latest races into the database.",
    parameters="[username]",
    examples=[
        "-i",
        "-i eiko",
    ],
)


class Download(Command):
    """Import a user's new races into the database."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    async def download(self, ctx: BotContext, username: str = None):
        """Resolve the username without importing, then run the importer with progress."""
        profile = await self.get_profile(ctx, username, auto_import=False)
        await run(ctx, profile)
