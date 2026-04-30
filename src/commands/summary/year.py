from dateutil.relativedelta import relativedelta
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.summary.races import run

info = {
    "name": "year",
    "aliases": ["y", "yesteryear", "yy", "ly"],
    "description": "Displays race information for a user in a given year.\n"
                   "Date defaults to the current year.",
    "parameters": "[username] [date]",
    "examples": [
        "-y",
        "-y eiko",
        "-y eiko 2024",
        "-ly eiko",
    ],
}


class Year(Command):
    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info["aliases"])
    async def year(self, ctx: BotContext, *args: str):
        date = ctx.flags.date

        if ctx.invoked_with in ["yesteryear", "yy", "ly"]:
            date -= relativedelta(years=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="year")
