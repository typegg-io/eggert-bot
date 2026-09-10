from dateutil.relativedelta import relativedelta
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.races import run
from context import BotContext

info = CommandInfo(
    name="year",
    aliases=["y", "yesteryear", "yy", "ly"],
    description="Displays race information for a user in a given year.",
    parameters="[username] [date:today]",
    examples=[
        "-y",
        "-y eiko",
        "-y eiko 2024",
        "-ly eiko",
    ],
)


class Year(Command):
    """Display a user's races in one year."""

    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info.aliases)
    async def year(self, ctx: BotContext, *args: str):
        """Resolve the date, stepping back one year when invoked as `-yesteryear`."""
        date = ctx.flags.date

        if ctx.invoked_with in ["yesteryear", "yy", "ly"]:
            date -= relativedelta(years=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="year")
