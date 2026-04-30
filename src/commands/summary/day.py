from dateutil.relativedelta import relativedelta
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.summary.races import run

info = {
    "name": "day",
    "aliases": ["d", "yesterday", "yd"],
    "description": "Displays race information for a user on a given day.\n"
                   "Date defaults to today.",
    "parameters": "[username] [date]",
    "examples": [
        "-d",
        "-d eiko",
        "-d eiko 2024-01-01",
        "-yd eiko",
    ],
}


class Day(Command):
    supported_flags = {"gamemode", "status", "language", "date"}

    @commands.command(aliases=info["aliases"])
    async def day(self, ctx: BotContext, *args: str):
        date = ctx.flags.date

        if ctx.invoked_with in ["yesterday", "yd"]:
            date -= relativedelta(days=1)

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, date, period="day")
