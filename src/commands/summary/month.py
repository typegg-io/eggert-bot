from typing import Optional

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.base import Command
from commands.summary.races import run
from utils.dates import parse_date

info = {
    "name": "month",
    "aliases": ["m", "yestermonth", "ym"],
    "description": "Displays race information for a given user and month\n"
                   "Date defaults to today",
    "parameters": "[username] [date]",
}


class Month(Command):
    @commands.command(aliases=info["aliases"])
    async def month(self, ctx, username: Optional[str] = "me", *date_args: str):
        date = parse_date("".join(date_args))

        if ctx.invoked_with in ["yestermonth", "ym"]:
            date -= relativedelta(months=1)

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, date, "month")
