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
from utils.messages import Message, Page, paginate_data
from utils.schemas import Profile
from utils.strings import format_duration, pp_display, quote_display

metrics = ["pp", "wpm"]

# The API sorts these two on lifetime counters, so no filter may travel with them.
COUNTER_SORTS = {"attempts": "attempts", "playtime": "playTime"}
COUNTER_TITLES = {"attempts": "Most Attempted Quotes", "playtime": "Most Time Typed"}

# Flags the counter sorts drop, since the API rejects every filter alongside them.
UNFILTERABLE = {"metric", "gamemode", "status", "number_range", "date_range"}

info = CommandInfo(
    name="best",
    aliases=["b", "most"],
    description="Displays a user's top 100 quote bests ordered by pp or WPM.\n"
                "Use `pp` or `wpm` to set the metric.\n"
                "Use `attempts` or `playtime` to rank your own quotes by how much you have typed them.\n"
                "Filter by WPM range: `>150`, `<120`, or `100-150`.",
    parameters="[username] [pp|wpm|attempts|playtime] [wpm range]",
    examples=[
        "-b",
        "-b eiko",
        "-b eiko wpm",
        "-b eiko >150",
        "-most attempts",
        "-most playtime",
    ],
    privacy=True,
)


class Best(Command):
    """Display a user's best 100 quotes."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range", "date_range"}

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

            await warn_unfilterable(ctx)
            await run_counters(ctx, profile, params.argument)
            return

        self.check_raw_pp(ctx, ctx.flags.metric == "pp")

        profile = await self.get_profile(ctx, params.username)
        await run(ctx, profile, ctx.flags.metric)


async def warn_unfilterable(ctx: BotContext) -> None:
    """Warn that a counter sort drops every filter the user typed."""
    explicit = getattr(ctx, "explicit_flags", {})
    ignored = [arg for name, arg in explicit.items() if name in UNFILTERABLE]

    if ignored:
        if len(ignored) == 1:
            flag_str = f"`{ignored[0]}`"
        else:
            flag_str = ", ".join(f"`{a}`" for a in ignored[:-1]) + f" and `{ignored[-1]}`"
        has_have = "has" if len(ignored) == 1 else "have"
        await ctx.send(f"-# :warning: {flag_str} {has_have} no effect on a lifetime counter")

    # The endpoint takes no universe parameter, so this one is unavailable rather than refused.
    if ctx.flags.language:
        await ctx.send("-# :warning: attempt counts are not scoped to a universe")


async def run_counters(ctx: BotContext, profile: Profile, sort: str) -> None:
    """Send the 100 quotes a user has attempted most, or spent the longest typing."""
    response = await get_quotes_api(
        profile["userId"],
        gamemode=None,
        status="any",
        sort=COUNTER_SORTS[sort],
        per_page=100,
    )

    quote_counters = response["quotes"]
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

    message = Message(
        ctx,
        title=COUNTER_TITLES[sort] + (" (Raw)" if raw else ""),
        pages=pages,
        profile=profile,
    )

    await message.send()


async def run(
    ctx: BotContext,
    profile: Profile,
    metric: str,
    reverse: bool = True,
) -> None:
    """Send a user's 100 best or worst quotes, paginated."""
    min_wpm, max_wpm = ctx.flags.number_range or (None, None)
    quotes = get_quotes()
    sources = get_sources()
    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", "pp", "wpm", "accuracy", "timestamp"],
        order_by=metric,
        reverse=reverse,
        limit=100,
        flags=ctx.flags,
        min_wpm=min_wpm,
        max_wpm=max_wpm,
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

    per_page = 5
    page_count = 20
    page_count = min(page_count, ((len(quote_bests) - 1) // per_page) + 1)
    pages = []
    for i in range(page_count):
        description = ""
        for quote in quote_bests[i * per_page:(i + 1) * per_page]:
            description += entry_formatter(quote)
        pages.append(Page(description=description, flag_title=True))

    pages = paginate_data(quote_bests, entry_formatter, 20, 5)
    title = f"{["Worst", "Best"][reverse]}{[" WPM", ""][metric == "pp"]} Quotes"

    if min_wpm is not None or max_wpm is not None:
        if min_wpm is not None and max_wpm is not None:
            title += f" {min_wpm:g}-{max_wpm:g} WPM"
        elif min_wpm is not None:
            title += f" ≥{min_wpm:g} WPM"
        else:
            title += f" <{max_wpm:g} WPM"

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()
