from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from config import DAILY_QUOTE_ROLE_ID
from utils import urls, dates
from utils.dates import parse_date, format_date
from utils.messages import Page, Message
from utils.strings import rank, discord_date, quote_display, username_with_flag

info = {
    "name": "dailyleaderboard",
    "aliases": ["daily", "dlb", "d10"],
    "description": "Displays the top 10 leaderboard for the daily quote",
    "parameters": "",
}


class DailyLeaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def dailyleaderboard(self, ctx: commands.Context, *args: str):
        arg = "".join(args)
        try:
            number = int(arg)
            daily_quote = await get_daily_quote(number=number)
        except ValueError:
            date = parse_date("".join(args))
            daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"))

        await display_daily_quote(ctx, daily_quote, f"Daily Quote #{daily_quote["dayNumber"]:,}")


async def display_daily_quote(
    ctx: commands.Context,
    daily_quote: dict,
    title: str,
    show_leaderboard: bool = True,
    show_champion=False,
    color=None,
    mention=False,
):
    quote = daily_quote["quote"]
    quote_id = quote["quoteId"]
    end_date = daily_quote["endDate"]
    leaderboard = daily_quote["leaderboard"]
    end = "Ends" if parse_date(end_date) > dates.now() else "Ended"

    description = quote_display(quote)
    if show_champion:
        def entry_formatter(data):
            return (
                f"{username_with_flag(data)} - "
                f"{data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%}) - {data["pp"]:,.0f} pp\n"
            )

        description = (
            f":trophy: **Champion: {entry_formatter(leaderboard[0])}**"
            f":medal: Runner-up: {entry_formatter(leaderboard[1])}\n"
            f"{description}"
        )

    if show_leaderboard and leaderboard:
        description += "\n\n**Top 10**\n"
        for i, score in enumerate(leaderboard):
            description += (
                f"{rank(i + 1)} {username_with_flag(score)} - "
                f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {score["pp"]:,.0f} pp - "
                f"{discord_date(score["timestamp"])}\n"
            )
        description = description[:-1]

    page = Page(
        title=(
            f"{title} - {format_date(parse_date(daily_quote["startDate"]))}\n"
            f"{quote_id}"
        ),
        description=description + f"\n\n{end} {discord_date(end_date)}",
        color=0xF1C40F,
    )

    message = Message(
        ctx,
        page=page,
        url=urls.race(quote_id),
        thumbnail=quote["source"]["thumbnailUrl"],
        content=f"<@&{DAILY_QUOTE_ROLE_ID}>" if mention else "",
        color=color,
    )

    await message.send()
