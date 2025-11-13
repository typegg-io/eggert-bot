from discord.abc import GuildChannel
from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from config import DAILY_QUOTE_ROLE_ID
from database.bot.recent_quotes import set_recent_quote
from utils import dates
from utils.dates import parse_date, format_date
from utils.messages import Page, Message
from utils.strings import rank, discord_date, quote_display, username_with_flag
from utils.urls import race_url

info = {
    "name": "dailyleaderboard",
    "aliases": ["daily", "dlb", "d10"],
    "description": "Displays the top 10 leaderboard for the daily quote",
    "parameters": "[date/day_number]",
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
            daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"), results=100)

        await display_daily_quote(ctx, daily_quote, f"Daily Quote #{daily_quote["dayNumber"]:,}")


async def display_daily_quote(
    ctx: commands.Context | GuildChannel,
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
    channel_id = ctx.channel.id if hasattr(ctx, "channel") else ctx.id
    set_recent_quote(channel_id, quote_id)

    description = quote_display(
        quote,
        display_author=True,
        display_status=True,
        display_racers_users=True,
        display_submitted_by=True,
        max_text_chars=1000,
    )

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
        description += "\n**Leaderboard**\n"
        for i, score in enumerate(leaderboard[:10]):
            bold = "**" if (
                hasattr(ctx, "user") and
                score["userId"] == ctx.user["userId"]
            ) else ""
            description += (
                f"{bold}{rank(i + 1)} {username_with_flag(score)} - "
                f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {score["pp"]:,.0f} pp - "
                f"{discord_date(score["timestamp"])}{bold}\n"
            )
        description = description[:-1]

    user_score = next((
        {"rank": i, "score": score}
        for i, score in enumerate(leaderboard)
        if score["userId"] == ctx.user["userId"]), {}
    )

    if user_score and user_score["rank"] > 9:
        score = user_score["score"]
        description += (
            f"\n\n**{user_score["rank"]} {username_with_flag(score)} - "
            f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {score["pp"]:,.0f} pp - "
            f"{discord_date(score["timestamp"])}**"
        )

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
        url=race_url(quote_id),
        thumbnail=quote["source"]["thumbnailUrl"],
        content=f"<@&{DAILY_QUOTE_ROLE_ID}>" if mention else "",
        color=color,
    )

    await message.send()
