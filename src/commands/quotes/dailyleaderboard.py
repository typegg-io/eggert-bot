from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from utils import urls
from utils.messages import Page, Message
from utils.strings import rank, escape_formatting, discord_date, quote_display

info = {
    "name": "dailyleaderboard",
    "aliases": ["daily", "dlb", "d10"],
    "description": "Displays the top 10 leaderboard for the daily quote",
    "parameters": "",
}


class DailyLeaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def dailyleaderboard(self, ctx: commands.Context):
        daily_quote = await get_daily_quote()
        quote = daily_quote["quote"]
        quote_id = quote["quoteId"]

        description = quote_display(quote) + "\n\n**Top 10**\n"
        for i, score in enumerate(daily_quote["leaderboard"]):
            country = score.get("country", None)
            flag = f":flag_{country.lower()}: " if country else ""
            pp = f"{score["pp"]:,.0f} pp - " if quote["ranked"] else ""
            description += (
                f"{rank(i + 1)} {flag}{escape_formatting(score["username"])} - "
                f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {pp}"
                f"{discord_date(score["timestamp"])}\n"
            )

        page = Page(
            title=f"Today's Daily Quote\n{quote_id}",
            description=description + f"\nEnds {discord_date(daily_quote["endDate"])}",
            color=0xF1C40F,
        )

        message = Message(
            ctx,
            page=page,
            url=urls.race(quote_id),
            thumbnail=quote["source"]["thumbnailUrl"],
        )

        await message.send()
