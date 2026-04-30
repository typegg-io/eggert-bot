from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils import strings
from utils.errors import NoRacesFiltered, NotSubscribed
from utils.messages import Message, paginate_data, Page
from utils.strings import quote_display

metrics = ["pp", "wpm"]
info = {
    "name": "best",
    "aliases": ["b"],
    "description": "Displays a user's top 100 quote bests ordered by pp or WPM.\n"
                   "Use `pp` or `wpm` to set the metric.\n"
                   "Filter by WPM range: `>150`, `<120`, or `100-150`.",
    "parameters": "[username] [pp|wpm] [wpm range]",
    "examples": [
        "-b",
        "-b eiko",
        "-b eiko wpm",
        "-b eiko >150"
    ],
}


class Best(Command):
    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range"}

    @commands.command(aliases=info["aliases"])
    async def best(self, ctx: BotContext, username: str = None):
        if ctx.flags.metric == "pp" and ctx.flags.raw and not ctx.user["isGgPlus"]:
            raise NotSubscribed("raw pp stats")

        profile = await self.get_profile(ctx, username)
        await run(ctx, profile, ctx.flags.metric)


async def run(
    ctx: BotContext,
    profile: dict,
    metric: str,
    reverse: bool = True,
):
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

    def entry_formatter(data):
        quote = dict(quotes[data["quoteId"]])
        quote["source"] = sources[quote["sourceId"]]
        pp_display = f"{data["pp"]:,.2f} pp - "
        if ctx.flags.raw and not ctx.user["isGgPlus"]:
            pp_display = ""
        return quote_display(quote) + (
            f"{pp_display}{data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%} Accuracy) - "
            f"{strings.discord_date(data["timestamp"])}\n\n"
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
