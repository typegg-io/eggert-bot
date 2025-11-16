from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils import strings
from utils.errors import NoRacesFiltered
from utils.messages import Message, paginate_data, Page
from utils.strings import get_argument, quote_display, get_flag_title

metrics = ["pp", "wpm"]
info = {
    "name": "best",
    "aliases": ["top", "b"],
    "description": "Displays a user's top 100 quotes\n"
                   "\\- `metric` defaults to pp",
    "parameters": "[username] [pp|wpm]",
}


class Best(Command):
    @commands.command(aliases=info["aliases"])
    async def best(self, ctx, username: Optional[str] = "me", metric: Optional[str] = "pp"):
        metric = get_argument(metrics, metric)
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str, reverse: bool = True):
    flags = ctx.flags
    quotes = get_quotes()
    sources = get_sources()
    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", "pp", "wpm", "accuracy", "timestamp"],
        order_by=metric,
        reverse=reverse,
        limit=100,
        flags=flags,
    )
    if not quote_bests:
        raise NoRacesFiltered(profile["username"])

    def entry_formatter(data):
        quote = dict(quotes[data["quoteId"]])
        quote["source"] = sources[quote["sourceId"]]
        return quote_display(quote) + (
            f"{data["pp"]:,.2f} pp - {data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%} Accuracy) - "
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
        pages.append(Page(description=description))

    pages = paginate_data(quote_bests, entry_formatter, 20, 5)
    title = f"{["Worst", "Best"][reverse]} {["WPM", "pp"][metric == "pp"]} Quotes"
    title += get_flag_title(flags)

    message = Message(
        ctx,
        title=title,
        pages=pages,
        profile=profile,
    )

    await message.send()
