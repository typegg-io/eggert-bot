from datetime import datetime, timezone

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.races import get_races
from graphs import activity
from utils.dates import current_utc_offset, format_utc_offset
from utils.errors import NoRacesFiltered
from utils.messages import Message, Page
from utils.schemas import Profile

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

info = CommandInfo(
    name="activity",
    aliases=["act", "clock"],
    description="Displays the hours of the day and the days of the week a user races most.\n"
                "Times follow your own timezone, which `-set timezone` changes.",
    parameters="[username]",
    examples=[
        "-activity",
        "-activity eiko",
    ],
)


class Activity(Command):
    """Display when in the day and the week a user races."""

    supported_flags = {"gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def activity(self, ctx: BotContext, *args: str):
        """Graph one user's typing activity."""
        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile)


def hour_label(hour: int) -> str:
    """Return an hour of the day on a 12-hour clock."""
    return f"{hour % 12 or 12} {"AM" if hour < 12 else "PM"}"


def hour_labels() -> list[str]:
    """Return the hour range every clock bar covers."""
    return [f"{hour_label(hour)} - {hour_label((hour + 1) % 24)}" for hour in range(24)]


def describe(labels: list[str], counts: list[int], total: int) -> str:
    """Return the race total with the busiest and the quietest period named."""
    def period_line(index: int) -> str:
        """Return a period's name above the races it holds and their share of the total."""
        return f"{labels[index]}\n{counts[index]:,} races ({counts[index] / total:.2%})"

    return (
        f"**Races:** {total:,}\n\n"
        f"**Most Active:** {period_line(counts.index(max(counts)))}\n\n"
        f"**Least Active:** {period_line(counts.index(min(counts)))}"
    )


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's races grouped by hour of the day and by day of the week."""
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["timestamp"],
        flags=ctx.flags,
    )

    if not race_list:
        raise NoRacesFiltered(profile["username"])

    utc_offset = current_utc_offset(ctx.user["timezone"])
    # Today's offset applies to every race, so the graph stays a rigid rotation of the UTC clock.
    fixed = timezone(utc_offset)
    hourly = [0] * 24
    weekly = [0] * 7

    for race in race_list:
        date = datetime.fromisoformat(race["timestamp"]).astimezone(fixed)
        hourly[date.hour] += 1
        # Python weeks open on Monday and the graph opens on Sunday.
        weekly[(date.weekday() + 1) % 7] += 1

    username = profile["username"]
    total = len(race_list)
    offset = format_utc_offset(utc_offset)

    pages = [
        Page(
            title="Daily Typing Activity",
            description=describe(hour_labels(), hourly, total),
            button_name="Daily",
            render=lambda: activity.render_clock(username, hourly, offset, ctx.user["theme"]),
            flag_title=True,
        ),
        Page(
            title="Weekly Typing Activity",
            description=describe(DAY_NAMES, weekly, total),
            button_name="Weekly",
            render=lambda: activity.render_weekly(username, weekly, offset, ctx.user["theme"]),
            flag_title=True,
        ),
    ]

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
