from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.sources import get_sources
from database.typegg.users import get_quote_bests
from utils import strings, urls
from utils.errors import invalid_argument
from utils.messages import Message, paginate_data, Page

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
        if metric not in metrics:
            return await ctx.send(embed=invalid_argument(metrics))

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str, reverse: bool = True):
    quotes = get_quotes()
    sources = get_sources()
    quote_bests = get_quote_bests(
        profile["userId"],
        metric=metric,
        reverse=reverse,
        limit=100,
    )

    def entry_formatter(data):
        quote = quotes[data["quoteId"]]
        text = quote["text"]
        source = sources[quote["sourceId"]]
        race = data
        return (
            f"[**{source["title"]}**]({urls.race(quote["quoteId"])}) "
            f"| {quote["difficulty"]:.2f}★ | {len(text)}c\n"
            f"\"{strings.truncate_clean(text, 60)}\"\n"
            f"{race["pp"]:,.2f} pp - {race["wpm"]:,.2f} WPM ({race["accuracy"]:.2%} Accuracy) - "
            f"{strings.discord_date(race["timestamp"])}\n\n"
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

    message = Message(
        ctx,
        title=f"{["Worst", "Best"][reverse]} {["WPM", "pp"][metric == "pp"]} Quotes",
        pages=pages,
        profile=profile,
    )

    await message.send()
