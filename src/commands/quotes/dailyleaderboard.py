from discord.abc import GuildChannel
from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from config import DAILY_QUOTE_ROLE_ID
from database.bot.recent_quotes import set_recent_quote
from utils import dates
from utils.dates import parse_date, format_date
from utils.messages import Page, Message, paginate_data
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

        title = f"Daily Quote #{daily_quote["dayNumber"]:,}"
        await display_daily_quote(ctx, daily_quote, title, paginate=True)


async def display_daily_quote(
    ctx: commands.Context | GuildChannel,
    daily_quote: dict,
    title: str,
    show_leaderboard: bool = True,
    show_champion=False,
    color=None,
    mention=False,
    paginate=False,
):
    quote = daily_quote["quote"]
    quote_id = quote["quoteId"]
    end_date = daily_quote["endDate"]
    leaderboard = daily_quote["leaderboard"]
    end = "Ends" if parse_date(end_date) > dates.now() else "Ended"
    channel_id = ctx.channel.id if hasattr(ctx, "channel") else ctx.id
    set_recent_quote(channel_id, quote_id)

    quote_description = quote_display(
        quote,
        display_author=True,
        display_status=True,
        display_racers_users=True,
        display_submitted_by=True,
        max_text_chars=1000,
    ) + f"\n{end} {discord_date(end_date)}\n"

    if show_champion:
        def entry_formatter(data):
            return (
                f"{username_with_flag(data)} - "
                f"{data["wpm"]:,.2f} WPM ({data["accuracy"]:.2%}) - {data["pp"]:,.0f} pp\n"
            )

        quote_description = (
            f":trophy: **Champion: {entry_formatter(leaderboard[0])}**"
            f":medal: Runner-up: {entry_formatter(leaderboard[1])}\n"
            f"{quote_description}"
        )

    def format_row(data):
        index, score = data["index"], data["score"]
        bold = "**" if (
            hasattr(ctx, "user") and
            score["userId"] == ctx.user["userId"]
        ) else ""
        return (
            f"{bold}{rank(index + 1)} {username_with_flag(score)} - "
            f"{score["wpm"]:,.2f} WPM ({score["accuracy"]:.2%}) - {score["pp"]:,.0f} pp - "
            f"{discord_date(score["timestamp"])}{bold}\n"
        )

    if show_leaderboard and leaderboard:
        for i in range(len(leaderboard)):
            leaderboard[i] = {"index": i, "score": leaderboard[i]}

        quote_description += "\n**Leaderboard**"
        description = ""
        for i, score in enumerate(leaderboard[:10]):
            description += format_row(score)

        user_score = next((
            row for row in leaderboard
            if hasattr(ctx, "user") and row["score"]["userId"] == ctx.user["userId"]), {}
        )

        if user_score and user_score["index"] > 9:
            description += f"\n{format_row(user_score)}"

    pages = [Page()]
    if show_leaderboard:
        if paginate:
            pages = paginate_data(leaderboard, format_row, page_count=10, per_page=10)
        pages[0].description = description

    message = Message(
        ctx,
        title=(
            f"{title} - {format_date(parse_date(daily_quote["startDate"]))}\n"
            f"{quote_id}"
        ),
        header=quote_description,
        pages=pages,
        url=race_url(quote_id),
        thumbnail=quote["source"]["thumbnailUrl"],
        content=f"<@&{DAILY_QUOTE_ROLE_ID}>" if mention else "",
        color=color or ctx.user["theme"]["embed"],
    )

    await message.send()
