from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.quotes.best import run
from context import BotContext

info = CommandInfo(
    name="worst",
    aliases=["bottom"],
    description="Displays a user's bottom 100 quotes\n"
                "Filter by a range of the metric: `>150`, `<120`, or `100-150`.",
    parameters="[username] [pp|wpm] [range]",
)


class Worst(Command):
    """Display a user's worst 100 quotes."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range", "date_range"}

    @commands.command(aliases=info.aliases)
    async def worst(self, ctx: BotContext, username: str = None):
        """Run the `-best` renderer in ascending order."""
        self.check_raw_pp(ctx, ctx.flags.metric == "pp")

        profile = await self.get_profile(ctx, username)
        await run(ctx, profile, ctx.flags.metric, reverse=False)
