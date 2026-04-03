from typing import Optional

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.base import Command
from commands.summary.races import run
from utils.dates import parse_date

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
    @commands.command(aliases=info["aliases"])
    async def year(self, ctx, username: Optional[str] = "me", *date_args: str):
        date = parse_date("".join(date_args))

        if ctx.invoked_with in ["yesteryear", "yy", "ly"]:
            date -= relativedelta(years=1)

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, date, "year")
