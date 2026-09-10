from dateutil.relativedelta import relativedelta
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.races import run
from context import BotContext

info = CommandInfo(
    name="week",
    aliases=["w", "yesterweek", "yw", "lw"],
    description="Displays race information for a user in a given week.",
    parameters="[username] [date:today]",
    examples=[
        "-w",
        "-w eiko",
        "-w eiko 2024-01-01",
        "-lw eiko",
    ],
)


class Week(Command):
    """Display a user's races in one week."""

    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info.aliases)
    async def week(self, ctx: BotContext, *args: str):
        """Resolve the date, stepping back one week when invoked as `-yesterweek`."""
        date = ctx.flags.date

        if ctx.invoked_with in ["yesterweek", "yw", "lw"]:
            date -= relativedelta(weeks=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="week")
