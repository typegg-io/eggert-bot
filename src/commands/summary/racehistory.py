from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.messages import Message, paginate_data
from utils.strings import discord_date, get_flag_title

info = {
    "name": "racehistory",
    "aliases": ["rh"],
    "description": "Displays a user's recent races",
    "parameters": "[user_id]",
    "privacy": True,
}


class RaceHistory(Command):
    @commands.command(aliases=info["aliases"])
    async def racehistory(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    only_historical_pbs = (
        profile["userId"] != ctx.user["userId"] and
        ctx.flags.gamemode not in ["quickplay", "lobby"]
    )

    race_list = await get_races(
        profile["userId"],
        reverse=True,
        flags=ctx.flags,
        only_historical_pbs=only_historical_pbs,
        limit=100,
    )

    quote_list = get_quotes()

    def formatter(race):
        if race["wpm"] == 0:
            desc = "DNF - "
        else:
            desc = (
                f"{race["wpm"]:,.2f} WPM - "
                f"{race["accuracy"]:.2%} - " +
                (f"{race["pp"]:,.2f} pp - " if race["pp"] > 0 else "")
            )

        desc += (
            f"{quote_list[race["quoteId"]]["difficulty"]:.2f}★ - "
            f"{discord_date(race["timestamp"])} - "
            f"[<:quote:1470361772132143277>](https://typegg.io/solo/{race["quoteId"]})\n"
        )

        return desc

    pages = paginate_data(race_list, formatter, page_count=4, per_page=25)

    message = Message(
        ctx,
        title="Race History" + get_flag_title(ctx.flags),
        pages=pages,
        profile=profile,
    )

    await message.send()
