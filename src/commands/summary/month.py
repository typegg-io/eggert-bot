from dateutil.relativedelta import relativedelta
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.summary.races import run

info = {
    "name": "month",
    "aliases": ["m", "yestermonth", "ym", "lm"],
    "description": "Displays race information for a user in a given month.\n"
                   "Date defaults to the current month.",
    "parameters": "[username] [date]",
    "examples": [
        "-m",
        "-m eiko",
        "-m eiko 2024-01",
        "-lm eiko",
    ],
}


class Month(Command):
    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info["aliases"])
    async def month(self, ctx: BotContext, *args: str):
        date = ctx.flags.date

        if ctx.invoked_with in ["yestermonth", "ym", "lm"]:
            date -= relativedelta(months=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="month")
