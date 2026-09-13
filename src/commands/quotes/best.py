from discord.ext import commands

from api.users import get_quotes as get_quotes_api
from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils.dates import discord_date
from utils.errors import BotError, NoRacesFiltered
from utils.flags import Flags, is_non_english
from utils.messages import Message, paginate_data
from utils.schemas import Profile
from utils.strings import format_duration, pp_display, quote_display

metrics = ["pp", "wpm"]

# The API sorts these two on lifetime counters, so no filter may travel with them.
COUNTER_SORTS = {"attempts": "attempts", "playtime": "playTime"}
COUNTER_TITLES = {"attempts": "Most Attempted Quotes", "playtime": "Most Time Typed"}

# Flags the counter sorts drop, since the API rejects every filter alongside them.
UNFILTERABLE = {"metric", "gamemode", "number_range", "length_range", "date_range"}

# A page this size costs the API no more than a page of 100, so ranked-only rarely needs a second.
FETCH_SIZE = 500
COUNTER_LIMIT = 100

info = CommandInfo(
    name="best",
    aliases=["b", "most"],
    description="Displays a user's top 100 quote bests ordered by pp or WPM.\n"
                "Use `pp` or `wpm` to set the metric.\n"
                "Use `attempts` or `playtime` to rank your own quotes by how much you have typed them.\n"
                "Filter by a range of the metric: `>150`, `<120`, or `100-150`.\n"
                "Filter by quote length: `>250c`, `<100c`, or `50-100c`.",
    parameters="[username] [pp|wpm|attempts|playtime] [range] [length]",
    examples=[
        "-b",
        "-b eiko",
        "-b eiko wpm",
        "-b eiko wpm >150",
        "-b eiko <100 pp",
        "-b eiko 50-100c",
        "-most attempts",
        "-most playtime",
    ],
    privacy=True,
)


class Best(Command):
    """Display a user's best 100 quotes."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range", "length_range", "date_range"}

    @commands.command(aliases=info.aliases)
    async def best(self, ctx: BotContext, *args):
        """Resolve the username and sort, then render the quote list."""
        params = self.extract_params(args, list(COUNTER_SORTS))

        if params.argument:
            profile = await self.get_profile(ctx, params.username)
            if profile["userId"] != ctx.user["userId"] and not ctx.user["isAdmin"]:
                raise BotError(
                    "Privacy Error",
                    "You may only view attempt counts for your own account",
                )

            await drop_unfilterable(ctx)
            await run_counters(ctx, profile, params.argument)
            return

        self.check_raw_pp(ctx, ctx.flags.metric == "pp")

        profile = await self.get_profile(ctx, params.username)
        await run(ctx, profile, ctx.flags.metric)


async def drop_unfilterable(ctx: BotContext) -> None:
    """Warn that a counter sort ignores the filters the user typed, then reset them."""
    explicit = getattr(ctx, "explicit_flags", {})
    ignored = [arg for name, arg in explicit.items() if name in UNFILTERABLE]
    stored_range = bool(ctx.flags.date_range) and "date_range" not in explicit

    defaults = Flags()
    for name in UNFILTERABLE:
        setattr(ctx.flags, name, getattr(defaults, name))

    if ignored:
        if len(ignored) == 1:
            flag_str = f"`{ignored[0]}`"
        else:
            flag_str = ", ".join(f"`{a}`" for a in ignored[:-1]) + f" and `{ignored[-1]}`"
        has_have = "has" if len(ignored) == 1 else "have"
        await ctx.send(f"-# :warning: {flag_str} {has_have} no effect on a lifetime counter")

    if stored_range:
        await ctx.send("-# :warning: time travel has no effect on a lifetime counter")

    # The endpoint takes no universe parameter, so this one is unavailable rather than refused.
    if is_non_english(ctx.flags):
        await ctx.send("-# :warning: attempt counts are not scoped to a universe")
        ctx.flags.language = None


async def fetch_counters(user_id: str, sort: str, status: str | None) -> list[dict]:
    """Return a user's top 100 counter rows, keeping only quotes the status flag allows."""
    counters = []
    page = 1

    while True:
        response = await get_quotes_api(
            user_id,
            gamemode=None,
            status="any",
            sort=sort,
            page=page,
            per_page=FETCH_SIZE,
        )

        rows = response["quotes"]
        if status and status != "any":
            rows = [row for row in rows if row["quote"]["ranked"] == (status == "ranked")]
        counters += rows

        if len(counters) >= COUNTER_LIMIT or page >= response["totalPages"]:
            break
        page += 1

    return counters[:COUNTER_LIMIT]


async def run_counters(ctx: BotContext, profile: Profile, sort: str) -> None:
    """Send the 100 quotes a user has attempted most, or spent the longest typing."""
    quote_counters = await fetch_counters(profile["userId"], COUNTER_SORTS[sort], ctx.flags.status)
    if not quote_counters:
        raise NoRacesFiltered(profile["username"])

    raw = ctx.flags.raw
    hide_raw_pp = raw and not ctx.user["isGgPlus"]
    wpm_key, pp_key = ("rawWpm", "rawPp") if raw else ("wpm", "pp")

    def entry_formatter(data) -> str:
        """Format one quote as a quote display, its best race, then its lifetime counters."""
        best_race = data["bestRace"]
        return quote_display(data["quote"]) + (
            f"{pp_display(best_race[pp_key], hide_raw_pp)} - {best_race[wpm_key]:,.2f} WPM "
            f"({best_race["accuracy"]:.2%} Accuracy) - {discord_date(best_race["timestamp"])}\n"
            f"{data["attempts"]:,} attempts - {format_duration(data["playTime"] / 1000)} typed\n\n"
        )

    pages = paginate_data(quote_counters, entry_formatter, 20, 5, flag_title=False)

    labels = [ctx.flags.status.title()] if ctx.flags.status else []
    if raw:
        labels.append("Raw")
    title = COUNTER_TITLES[sort] + (f" ({", ".join(labels)})" if labels else "")

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()


def range_label(bounds: tuple, unit: str) -> str:
    """Return a range for a title, like `100-150 WPM`, `≥150 WPM` or `<120 WPM`."""
    min_value, max_value = bounds
    if min_value is not None and max_value is not None:
        return f"{min_value:g}-{max_value:g} {unit}"
    if min_value is not None:
        return f"≥{min_value:g} {unit}"
    return f"<{max_value:g} {unit}"


async def run(
    ctx: BotContext,
    profile: Profile,
    metric: str,
    reverse: bool = True,
) -> None:
    """Send a user's 100 best or worst quotes, paginated."""
    min_value, max_value = ctx.flags.number_range or (None, None)
    quotes = get_quotes()
    sources = get_sources()
    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", "pp", "wpm", "accuracy", "timestamp"],
        order_by=metric,
        reverse=reverse,
        limit=100,
        flags=ctx.flags,
        min_value=min_value,
        max_value=max_value,
    )
    if not quote_bests:
        raise NoRacesFiltered(profile["username"])

    hide_raw_pp = ctx.flags.raw and not ctx.user["isGgPlus"]

    def entry_formatter(data) -> str:
        """Format one quote best as a quote display followed by the score."""
        quote = dict(quotes[data["quoteId"]])
        quote["source"] = sources[quote["sourceId"]]
        pp = pp_display(data["pp"], hide_raw_pp)
        return quote_display(quote) + (
            f"{pp} - {data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%} Accuracy) - "
            f"{discord_date(data["timestamp"])}\n\n"
        )

    pages = paginate_data(quote_bests, entry_formatter, 20, 5)
    title = f"{["Worst", "Best"][reverse]}{[" WPM", ""][metric == "pp"]} Quotes"

    unit = "pp" if metric == "pp" else "WPM"
    ranges = []
    if ctx.flags.number_range:
        ranges.append(range_label(ctx.flags.number_range, unit))
    if ctx.flags.length_range:
        ranges.append(range_label(ctx.flags.length_range, "chars"))
    if ranges:
        title += " " + ", ".join(ranges)

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()
