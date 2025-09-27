from typing import Optional

from discord.ext import commands

from api.users import get_quotes
from commands.base import Command
from utils import strings, urls
from utils.errors import no_races, invalid_argument
from utils.messages import Message, paginate_data

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

        profile = await self.get_profile(ctx, username)
        await run(ctx, profile, metric)


def entry_formatter(data):
    quote = data["quote"]
    text = quote["text"]
    race = data["bestRace"]
    return (
        f"[**{quote["source"]["title"]}**]({urls.race(quote["quoteId"])}) "
        f"| {quote["difficulty"]:.2f}★ | {len(text)}c | Rank #{data["globalRank"]}/{quote["uniqueUsers"]}\n"
        f"\"{strings.truncate_clean(text, 60)}\"\n"
        f"{race["pp"]:,.2f} pp - {race["wpm"]:,.2f} WPM ({race["accuracy"]:.2%} Accuracy) - "
        f"{strings.discord_date(race["timestamp"])}\n\n"
    )


async def run(ctx: commands.Context, profile: dict, metric: str, reverse: bool = True):
    results = await get_quotes(
        profile["username"],
        sort=metric,
        status="ranked",
        reverse=reverse,
        per_page=100,
    )
    top_quotes = results["quotes"]
    if not top_quotes:
        return await ctx.send(embed=no_races())

    pages = paginate_data(top_quotes, entry_formatter, 20, 5)

    message = Message(
        ctx,
        title=f"{["Worst", "Best"][reverse]} {["WPM", "pp"][metric == "pp"]} Quotes",
        pages=pages,
        profile=profile,
    )

    await message.send()
