from bisect import bisect_left
from dataclasses import replace
from typing import NamedTuple

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.graphs.linegraph import get_total_pp_over_time
from commands.summary.races import build_stat_fields
from context import BotContext
from database.typegg.races import get_races
from utils.errors import BotError, NoRacesFiltered, NumberGreaterThan
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import format_duration, parse_duration, parse_duration_args
from utils.windows import Window, marathon_windows, race_span, race_times, top_disjoint_windows

DEFAULT_PERIOD = 86400

info = CommandInfo(
    name="marathon",
    aliases=["42"],
    description="Displays the most races a user completed, or the most pp they gained, within a period of time.\n"
                "Period can be given as a duration (`1h30m`) or a number of seconds.",
    parameters="[username] <category:races|pp> <period:1d>",
    examples=[
        "-marathon",
        "-marathon pp",
        "-marathon eiko pp 1h",
    ],
)


class WindowData(NamedTuple):
    """A user's races with the amount standing before and after each one."""

    races: list
    starts: list[float]
    ends: list[float]
    before: list[float]
    after: list[float]


class Marathon(Command):
    """Display a user's busiest stretch inside a fixed period of time."""

    supported_flags = {"metric", "gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def marathon(self, ctx: BotContext, *args: str):
        """Read the period and the category, then find the best windows."""
        period = take_duration(ctx, DEFAULT_PERIOD)
        params = self.extract_params(drop_durations(args), extract=["races"])
        profile = await self.get_profile(ctx, params.username)

        await run(ctx, profile, "pp" if is_pp_category(ctx) else "races", period)


def take_duration(ctx: BotContext, default: float) -> float:
    """Return the duration the user gave, written either as a duration string or as seconds."""
    seconds = parse_duration_args(ctx.raw_args)

    if seconds is None:
        seconds = abs(ctx.flags.number) if ctx.flags.number is not None else default

    if seconds <= 0:
        raise NumberGreaterThan(0)

    return seconds


def drop_durations(args: tuple) -> list:
    """Return the arguments that are not duration tokens."""
    return [arg for arg in args if parse_duration(arg) is None]


def is_pp_category(ctx: BotContext) -> bool:
    """Return whether the user asked for the pp category."""
    return ctx.explicit_flags.get("metric", "").lstrip("-").lower() == "pp"


async def get_window_data(ctx: BotContext, profile: Profile, by_pp: bool) -> WindowData:
    """Fetch a user's races along with the running amount their windows are measured against."""
    flags = ctx.flags

    if by_pp and flags.status != "ranked":
        await ctx.send("-# :warning: only ranked races earn pp")
        flags.status = "ranked"

    # A total counts every earlier race, so a date range narrows the result instead of the query.
    race_list = await get_races(
        user_id=profile["userId"],
        include_dnf=False,
        flags=replace(flags, date_range=None) if by_pp else flags,
    )

    if not race_list:
        raise NoRacesFiltered(profile["username"])

    starts, ends = race_times(race_list)

    if by_pp:
        after = get_total_pp_over_time(race_list)
        before = [0.0] + after[:-1]
    else:
        before = [float(i) for i in range(len(race_list))]
        after = [float(i + 1) for i in range(len(race_list))]

    if by_pp and flags.date_range:
        start_date, end_date = flags.date_range
        first = bisect_left(ends, start_date.timestamp())
        last = bisect_left(ends, end_date.timestamp())

        if first == last:
            raise NoRacesFiltered(profile["username"])

        race_list, starts, ends = race_list[first:last], starts[first:last], ends[first:last]
        before, after = before[first:last], after[first:last]

    return WindowData(race_list, starts, ends, before, after)


def window_line(data: WindowData, window: Window, category: str) -> str:
    """Return one line describing what a window holds and which races it covers."""
    start, end, value = window
    races = end - start
    span = format_duration(data.ends[end - 1] - data.starts[start], show_seconds=False)
    numbers = race_span(data.races[start], data.races[end - 1])

    if category == "pp":
        return f"**+{value:,.2f} pp** over {races:,} races in {span} {numbers}"

    return f"**{races:,}** races in {span} {numbers}"


async def run(ctx: BotContext, profile: Profile, category: str, period: float) -> None:
    """Send the 10 best non-overlapping windows of a period, by races or by pp gained."""
    data = await get_window_data(ctx, profile, category == "pp")

    windows = marathon_windows(data.starts, data.ends, period, data.before, data.after)
    windows.sort(key=lambda window: -window[2])
    top_windows = top_disjoint_windows(windows)

    if not top_windows:
        raise BotError(
            "No pp Gained",
            "User has gained no pp in this range",
        )

    best = top_windows[0]
    period_title = format_duration(period)
    subject = "pp" if category == "pp" else "Races"

    pages = [Page(
        title=f"Most {subject} in {period_title}",
        description=window_line(data, best, category),
        fields=build_stat_fields(profile, data.races[best[0]:best[1]], ctx.flags),
        button_name="Best",
        flag_title=True,
    )]

    top_10 = ""

    for i, window in enumerate(top_windows, start=1):
        top_10 += f"{i}. {window_line(data, window, category)}\n"

    pages.append(Page(
        title=f"Top 10 {subject} Marathons ({period_title})",
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
