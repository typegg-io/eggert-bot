from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.quotes.best import run
from context import BotContext
from utils.errors import NotSubscribed

info = CommandInfo(
    name="worst",
    aliases=["bottom"],
    description="Displays a user's bottom 100 quotes\n"
                "\\- `metric` defaults to pp",
    parameters="[username] [pp|wpm]",
)


class Worst(Command):
    """Display a user's worst 100 quotes."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range"}

    @commands.command(aliases=info.aliases)
    async def worst(self, ctx: BotContext, username: str = None):
        """Run the `-best` renderer in ascending order."""
        if ctx.flags.metric == "pp" and ctx.flags.raw and not ctx.user["isGgPlus"]:
            raise NotSubscribed("raw pp stats")

        profile = await self.get_profile(ctx, username)
        await run(ctx, profile, ctx.flags.metric, reverse=False)
