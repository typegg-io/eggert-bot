from discord.ext import commands

from api.quotes import get_quote
from commands.base import Command
from utils import urls
from utils.messages import Page, Message
from utils.strings import rank, discord_date, quote_display, username_with_flag

info = {
    "name": "quoteleaderboard",
    "aliases": ["qlb", "10"],
    "description": "Displays the top 10 leaderboard for a specific quote",
    "parameters": "<quote_id>",
}


class QuoteLeaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def quoteleaderboard(self, ctx: commands.Context, quote_id: str):
        quote = await get_quote(quote_id)
        await run(ctx, quote)


async def run(ctx: commands.Context, quote: dict):
    description = quote_display(quote) + "\n\n**Top 10**\n"

    leaderboard_string = ""
    for i, score in enumerate(quote["leaderboard"]):
        pp = f"{score["pp"]:,.0f} pp - " if quote["ranked"] else ""
        leaderboard_string += (
            f"{rank(i + 1)} {username_with_flag(score)} - "
            f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {pp}"
            f"{discord_date(score["timestamp"])}\n"
        )

    page = Page(
        title=quote["quoteId"],
        description=description + leaderboard_string,
    )

    message = Message(
        ctx,
        page=page,
        url=urls.race(quote["quoteId"]),
        thumbnail=quote["source"]["thumbnailUrl"],
    )

    await message.send()
