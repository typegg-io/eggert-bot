from dataclasses import replace
from datetime import datetime

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.graphs.linegraph import get_total_pp_over_time
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.dates import discord_date, get_start_end_dates, resolve_date_range
from utils.errors import NoRacesFiltered
from utils.flags import is_multiplayer
from utils.messages import Message, paginate_data
from utils.schemas import Profile
from utils.strings import date_range_display, format_duration, pp_display

PERIODS = {"day": "Days", "week": "Weeks", "month": "Months", "year": "Years"}
SORTS = ["date", "races", "playtime", "accuracy"]
SORT_TITLES = {"date": "Date", "races": "Races", "playtime": "Time", "accuracy": "Accuracy", "wpm": "WPM", "pp": "pp"}
REVERSE_WORDS = ["least", "worst", "oldest"]

info = CommandInfo(
    name="racehistory",
    aliases=["rh"],
    description="Displays a user's recent race history.\n"
                "Add `day`, `week`, `month` or `year` to group races by period instead.\n"
                "Periods sort by `date`, `races`, `time`, `accuracy`, `wpm` or `pp` gained. "
                "Add `least` to reverse the order.",
    parameters="[username] [period] [sort:date]",
    examples=[
        "-rh",
        "-rh eiko",
        "-rh week",
        "-rh day wpm",
        "-rh month pp",
        "-rh year time least",
    ],
    privacy=True,
)


class RaceHistory(Command):
    """Display a user's recent races, or their races grouped by period."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def racehistory(self, ctx: BotContext, *args: str):
        """Resolve the period and sort, then render the history."""
        period = ctx.flags.period if ctx.flags.period in PERIODS else None
        if period is None:
            profile = await self.get_profile(ctx, args[0] if args else None)
            return await run(ctx, profile)

        params = self.extract_params(args, SORTS)
        reverse_params = self.extract_params(params.remaining, REVERSE_WORDS)
        metric = ctx.explicit_flags.get("metric", "").lstrip("-").lower()
        sort = metric or params.argument or "date"

        self.check_raw_pp(ctx, sort == "pp")
        profile = await self.get_profile(ctx, reverse_params.username)

        # A period word groups here, so only a typed range or time travel narrows the races.
        ctx.flags.date_range = resolve_date_range(
            replace(ctx.flags, period=None),
            ctx.user["timezone"],
            (ctx.user["startDate"], ctx.user["endDate"]),
        )

        await run_periods(ctx, profile, period, sort, reverse=reverse_params.argument is None)


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's last 100 races, paginated."""
    only_historical_pbs = (
        profile["userId"] != ctx.user["userId"] and
        not is_multiplayer(ctx.flags)
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
        title="Race History",
        pages=pages,
        profile=profile,
    )

    await message.send()


def group_races(race_list: list, totals: list[float] | None, period: str, tz, date_range) -> list[dict]:
    """Return one summary per period a user raced in, oldest first."""
    history = []

    for i, race in enumerate(race_list):
        date = datetime.fromisoformat(race["timestamp"])
        if date_range and not date_range[0] <= date < date_range[1]:
            continue

        if not history or date >= history[-1]["end"]:
            start, end = get_start_end_dates(date, period, tz)
            history.append({
                "start": start, "end": end, "races": 0, "wpm": 0, "accuracy": 0, "playtime": 0,
                "before": totals[i - 1] if totals and i > 0 else 0,
            })

        entry = history[-1]
        entry["races"] += 1
        entry["wpm"] += race["wpm"]
        entry["accuracy"] += race["accuracy"]
        entry["playtime"] += race["duration"] / 1000
        entry["pp"] = totals[i] - entry["before"] if totals else 0

    for entry in history:
        entry["wpm"] /= entry["races"]
        entry["accuracy"] /= entry["races"]

    return history


def period_label(entry: dict, period: str, tz) -> str:
    """Return the name of a summary's period in the user's timezone."""
    start = entry["start"].astimezone(tz)
    if period == "month":
        return start.strftime("%B %Y")
    if period == "year":
        return start.strftime("%Y")
    return date_range_display(entry["start"], entry["end"], tz)


async def run_periods(ctx: BotContext, profile: Profile, period: str, sort: str, reverse: bool) -> None:
    """Send a user's races grouped by period, sorted by one stat."""
    flags = ctx.flags
    tz = ctx.user["timezone"]
    show_pp = flags.status == "ranked"

    if sort == "pp" and not show_pp:
        await ctx.send("-# :warning: only ranked races earn pp")
        flags.status = "ranked"
        show_pp = True

    # A pp total counts every earlier race, so the range narrows the grouping instead of the query.
    race_list = await get_races(
        profile["userId"],
        columns=["quoteId", "pp", "wpm", "accuracy", "duration", "timestamp"],
        include_dnf=False,
        flags=replace(flags, date_range=None) if show_pp else flags,
    )
    totals = get_total_pp_over_time(race_list) if show_pp else None
    history = group_races(race_list, totals, period, tz, flags.date_range)

    if not history:
        raise NoRacesFiltered(profile["username"])

    sort_key = "start" if sort == "date" else sort
    history.sort(key=lambda entry: entry[sort_key], reverse=reverse)
    hide_raw_pp = flags.raw and not ctx.user["isGgPlus"]

    def formatter(entry: dict) -> str:
        """Format one period's summary."""
        pp = ("" if hide_raw_pp else "+") + pp_display(entry["pp"], hide_raw_pp) + " / " if show_pp else ""
        return (
            f"**{period_label(entry, period, tz)}**\n"
            f"{entry["races"]:,} Races / {pp}{format_duration(entry["playtime"])}\n"
            f"{entry["wpm"]:,.2f} WPM ({entry["accuracy"]:.2%} Accuracy)\n\n"
        )

    prefix = "" if reverse else ("Oldest " if sort == "date" else "Least ")
    message = Message(
        ctx,
        title=f"Race History - {PERIODS[period]} (By {prefix}{SORT_TITLES[sort]})",
        pages=paginate_data(history, formatter, page_count=20, per_page=10),
        profile=profile,
    )

    await message.send()
