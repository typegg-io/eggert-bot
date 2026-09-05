from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from config import GENERAL_CHANNEL_ID
from context import BotContext
from utils.messages import usable_in

info = CommandInfo(
    name="brothers",
    aliases=[],
    description="Posts brothers link.",
)


class Brothers(Command):
    """Post the brothers link."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @usable_in(GENERAL_CHANNEL_ID)
    async def brothers(self, ctx: BotContext):
        """Send the link, in the general channel only."""
        await ctx.send("https://www.youtube.com/watch?v=2BWgmYHAxs4")
