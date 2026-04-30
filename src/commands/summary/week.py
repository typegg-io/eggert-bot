from dateutil.relativedelta import relativedelta
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.summary.races import run

info = {
    "name": "week",
    "aliases": ["w", "yesterweek", "yw", "lw"],
    "description": "Displays race information for a user in a given week.\n"
                   "Date defaults to the current week.",
    "parameters": "[username] [date]",
    "examples": [
        "-w",
        "-w eiko",
        "-w eiko 2024-01-01",
        "-lw eiko",
    ],
}


class Week(Command):
    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info["aliases"])
    async def week(self, ctx: BotContext, *args: str):
        date = ctx.flags.date

        if ctx.invoked_with in ["yesterweek", "yw", "lw"]:
            date -= relativedelta(weeks=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="week")
