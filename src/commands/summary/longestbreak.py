from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.races import get_races
from utils.dates import discord_date
from utils.errors import BotError, NoRacesFiltered
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import format_duration
from utils.windows import race_times

info = CommandInfo(
    name="longestbreak",
    aliases=["break", "breaks"],
    description="Displays the longest a user has gone between two races.",
    parameters="[username]",
    examples=[
        "-longestbreak",
        "-longestbreak eiko",
    ],
)


class LongestBreak(Command):
    """Display the longest stretches a user went without racing."""

    supported_flags = {"gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def longestbreak(self, ctx: BotContext, *args: str):
        """Resolve the username, then find the longest gaps between races."""
        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile)


def race_line(race: dict, verb: str) -> str:
    """Return the race a break runs from or to, with the day it happened."""
    return f"{verb} race #{race["raceNumber"]:,} - {discord_date(race["timestamp"], "D")}"


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send the longest break between two races, then the top 10."""
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["raceNumber", "timestamp", "duration"],
        flags=ctx.flags,
    )
    if not race_list:
        raise NoRacesFiltered(profile["username"])

    if len(race_list) < 2:
        raise BotError(
            "Not Enough Races",
            "User needs at least 2 races to have taken a break",
        )

    starts, ends = race_times(race_list)
    # A break is idle time, so it runs from the end of one race to the start of the next.
    breaks = [(starts[i + 1] - ends[i], i) for i in range(len(race_list) - 1)]
    breaks.sort(reverse=True)
    top_breaks = breaks[:10]

    longest, index = top_breaks[0]

    pages = [Page(
        title="Longest Break",
        description=(
            f"**{format_duration(longest, show_seconds=False)}**\n"
            f"{race_line(race_list[index], "Starting on")}\n"
            f"{race_line(race_list[index + 1], "Ending on")}"
        ),
        button_name="Longest",
        flag_title=True,
    )]

    top_10 = ""

    for i, (gap, start) in enumerate(top_breaks, start=1):
        top_10 += (
            f"{i}. **{format_duration(gap, show_seconds=False)}** "
            f"{race_line(race_list[start], "starting on")}\n"
        )

    pages.append(Page(
        title="Top 10 Longest Breaks",
        description=top_10,
        button_name="Top 10",
        flag_title=True,
    ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
