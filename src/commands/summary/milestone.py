from bisect import bisect_left

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.marathon import WindowData, get_window_data
from context import BotContext
from database.bot.recent_quotes import set_recent_quote
from database.typegg.quotes import get_quote
from utils.dates import discord_date, parse_date
from utils.errors import BotError, MissingArguments, NumberGreaterThan
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import format_duration, pp_display, quote_display

CATEGORIES = ["races", "quotes"]
UNITS = {"races": "Races", "quotes": "Quotes", "pp": "pp", "wpm": "WPM"}

info = CommandInfo(
    name="milestone",
    aliases=["ms"],
    description="Displays the race on which a user reached a milestone.\n"
                "Category can be `races`, `quotes`, `pp` or `wpm`.",
    parameters="[username] [milestone] <category:races|quotes|pp|wpm>",
    examples=[
        "-milestone 1000",
        "-ms 10k races",
        "-ms eiko 5000 pp",
        "-ms eiko 200 wpm",
    ],
)


class Milestone(Command):
    """Display the race on which a user reached a milestone."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def milestone(self, ctx: BotContext, *args: str):
        """Read the milestone and its category, then find the race that reached it."""
        params = self.extract_params(args, CATEGORIES)
        category = take_category(ctx, params.argument)
        self.check_raw_pp(ctx, category == "pp")
        profile = await self.get_profile(ctx, params.username)

        await run(ctx, profile, category, ctx.flags.number)


def take_category(ctx: BotContext, argument: str | None) -> str:
    """Return the category to measure, reading pp and wpm off the metric flag."""
    metric = ctx.explicit_flags.get("metric", "").lstrip("-").lower()
    if metric in ["pp", "wpm"]:
        return metric

    return argument or "races"


def amount_display(category: str, milestone: float) -> str:
    """Return a milestone amount with the unit it counts in."""
    value = f"{milestone:,.0f}" if milestone == int(milestone) else f"{milestone:,.2f}"

    return f"{value} {UNITS[category]}"


def progress_values(data: WindowData, category: str) -> list[float]:
    """Return the running amount each race leaves a user at, for one category."""
    if category == "quotes":
        seen = set()
        counts = []
        for race in data.races:
            seen.add(race["quoteId"])
            counts.append(float(len(seen)))

        return counts

    if category == "wpm":
        # The search bisects this list, so a speed has to be carried forward as a running maximum.
        best = 0.0
        peaks = []
        for race in data.races:
            best = max(best, race["wpm"])
            peaks.append(best)

        return peaks

    return data.after


async def run(ctx: BotContext, profile: Profile, category: str, number: float | None) -> None:
    """Send the race on which a user reached a milestone, with its quote and stats."""
    if number is None:
        raise MissingArguments

    milestone = abs(number)
    if category in CATEGORIES:
        milestone = round(milestone)
    if milestone <= 0:
        raise NumberGreaterThan(0)

    data = await get_window_data(ctx, profile, category == "pp")
    progress = progress_values(data, category)
    index = bisect_left(progress, milestone)
    amount = amount_display(category, milestone)

    if index == len(progress):
        raise BotError(
            "Milestone Not Reached",
            f"User has not reached {amount}",
        )

    race = data.races[index]
    quote = get_quote(race["quoteId"])
    set_recent_quote(ctx.channel.id, race["quoteId"])

    elapsed = parse_date(race["timestamp"]).timestamp() - parse_date(profile["joinDate"]).timestamp()
    description = f"Completed {discord_date(race["timestamp"])}\n"

    if elapsed > 0:
        description += f"Took {format_duration(elapsed, show_seconds=False)} since joining\n"

    description += (
        f"\n{quote_display(quote, 1000, display_status=True)}"
        f"**Score:** {pp_display(race["pp"], ctx.flags.raw and not ctx.user["isGgPlus"])}\n"
        f"**Speed:** {race["wpm"]:,.2f} WPM\n"
        f"**Accuracy:** {race["accuracy"]:.2%}\n"
    )

    page = Page(
        title=f"Milestone - {amount} - Race #{race["raceNumber"]:,}",
        description=description,
        flag_title=True,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
