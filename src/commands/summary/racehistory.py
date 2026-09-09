from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.dates import discord_date
from utils.messages import Message, paginate_data
from utils.schemas import Profile
from utils.strings import pp_display

info = CommandInfo(
    name="racehistory",
    aliases=["rh"],
    description="Displays a user's recent race history.",
    parameters="[username]",
    examples=[
        "-rh",
        "-rh eiko",
    ],
    privacy=True,
)


class RaceHistory(Command):
    """Display a user's recent races."""

    supported_flags = {"raw", "gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def racehistory(self, ctx: BotContext, username: str = None):
        """Resolve the username, then render their recent races."""
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's last 100 races, paginated."""
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
    hide_raw_pp = ctx.flags.raw and not ctx.user["isGgPlus"]

    def formatter(race) -> str:
        """Format one race as a single line, or as a DNF."""
        if race["wpm"] == 0:
            desc = "DNF - "
        else:
            desc = (
                f"{race["wpm"]:,.2f} WPM - "
                f"{race["accuracy"]:.2%} - " +
                (f"{pp_display(race["pp"], hide_raw_pp)} - " if race["pp"] > 0 else "")
            )

        desc += (
            f"{quote_list[race["quoteId"]]["difficulty"]:.2f}★ - "
            f"{discord_date(race["timestamp"])} - "
            f"[<:quote_link:1483237184482836540>](https://typegg.io/solo/{race["quoteId"]})\n"
        )

        return desc

    pages = paginate_data(race_list, formatter, page_count=4, per_page=25)

    message = Message(
        ctx,
        title="Race History" + (" (Raw)" if ctx.flags.raw else ""),
        pages=pages,
        profile=profile,
    )

    await message.send()
