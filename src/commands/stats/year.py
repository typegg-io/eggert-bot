from typing import Optional

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.base import Command
from commands.stats.races import run
from utils.dates import parse_date

info = {
    "name": "year",
    "aliases": ["y", "yesteryear", "yy"],
    "description": "Displays race information for a given user and year\n"
                   "Date defaults to today",
    "parameters": "[username] [date]",
}


class Year(Command):
    @commands.command(aliases=info["aliases"])
    async def year(self, ctx, username: Optional[str] = "me", *date_args: str):
        date = parse_date("".join(date_args))

        if ctx.invoked_with in ["yesteryear", "yy"]:
            date -= relativedelta(years=1)

        profile = await self.get_profile(ctx, username, races_required=True)
        await run(ctx, profile, date, "year")
