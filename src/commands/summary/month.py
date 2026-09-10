from dateutil.relativedelta import relativedelta
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.races import run
from context import BotContext

info = CommandInfo(
    name="month",
    aliases=["m", "yestermonth", "ym", "lm"],
    description="Displays race information for a user in a given month.",
    parameters="[username] [date:today]",
    examples=[
        "-m",
        "-m eiko",
        "-m eiko 2024-01",
        "-lm eiko",
    ],
)


class Month(Command):
    """Display a user's races in one month."""

    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info.aliases)
    async def month(self, ctx: BotContext, *args: str):
        """Resolve the date, stepping back one month when invoked as `-yestermonth`."""
        date = ctx.flags.date

        if ctx.invoked_with in ["yestermonth", "ym", "lm"]:
            date -= relativedelta(months=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="month")
