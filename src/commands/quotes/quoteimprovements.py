from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from database.typegg.sources import get_sources
from utils.dates import discord_date
from utils.errors import BotError, NoRacesFiltered
from utils.messages import Message, paginate_data
from utils.schemas import Profile
from utils.strings import quote_display

SORTS = ["recent", "best", "worst"]
TITLES = {"recent": "Recent", "best": "Biggest", "worst": "Smallest"}

info = CommandInfo(
    name="quoteimprovements",
    aliases=["qi"],
    description="Displays every time a user beat their own best on a quote.\n"
                "Sort can be `recent`, `best` or `worst`.\n"
                "Use `pp` or `wpm` to set the metric.",
    parameters="[username] <sort:recent|best|worst>",
    examples=[
        "-quoteimprovements",
        "-qi wpm",
        "-qi eiko best",
    ],
)


class QuoteImprovements(Command):
    """Display every time a user raised their own best on a quote."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def quoteimprovements(self, ctx: BotContext, *args: str):
        """Resolve the sort order, then list the improvements."""
        params = self.extract_params(args, SORTS)
        self.check_raw_pp(ctx, ctx.flags.metric == "pp")
        profile = await self.get_profile(ctx, params.username)

        await run(ctx, profile, params.argument or "recent")


def find_improvements(race_list: list, metric: str) -> list[tuple]:
    """Return every race that beat the standing best on its quote, oldest first."""
    improvements = []
    bests = {}

    for race in race_list:
        score = race[metric]
        # A quit scores zero, so it is neither a best nor a baseline to improve on.
        if not score:
            continue

        best = bests.get(race["quoteId"])
        if best is None or score > best[metric]:
            bests[race["quoteId"]] = race
            if best is not None:
                improvements.append((best, race, score - best[metric]))

    return improvements


async def run(ctx: BotContext, profile: Profile, sort: str) -> None:
    """Send the times a user raised their own best on a quote, paginated."""
    metric = ctx.flags.metric
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["quoteId", "raceNumber", "pp", "wpm", "timestamp"],
        flags=ctx.flags,
    )
    if not race_list:
        raise NoRacesFiltered(profile["username"])

    improvements = find_improvements(race_list, metric)
    if not improvements:
        raise BotError(
            "No Improvements",
            f"{profile["username"]} has never beaten their own best on a quote in this range",
        )

    if sort == "recent":
        improvements.reverse()
    else:
        improvements.sort(key=lambda improvement: improvement[2], reverse=sort == "best")

    quotes = get_quotes()
    sources = get_sources()
    unit = "pp" if metric == "pp" else "WPM"

    def entry_formatter(data) -> str:
        """Format one improvement as the quote, the two scores and the gain between them."""
        previous, race, gain = data
        quote = dict(quotes[race["quoteId"]])
        quote["source"] = sources[quote["sourceId"]]

        return quote_display(quote) + (
            f"{previous[metric]:,.2f} ➜ {race[metric]:,.2f} {unit} (+{gain:,.2f}) - "
            f"#{previous["raceNumber"]:,} ➜ #{race["raceNumber"]:,} - "
            f"{discord_date(race["timestamp"])}\n\n"
        )

    pages = paginate_data(improvements, entry_formatter, 20, 5)
    title = f"{TITLES[sort]}{"" if metric == "pp" else " WPM"} Quote Improvements"

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()
