from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from commands.daily.dailyleaderboard import daily_quote_display
from config import DAILY_QUOTE_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote
from database.typegg.quotes import get_quote
from graphs import daily as daily_graph
from utils.dates import parse_date, format_date
from utils.keylogs import get_keystroke_data
from utils.messages import Page, Message, usable_in
from utils.urls import race_url

info = {
    "name": "dailygraph",
    "aliases": ["dg"],
    "description": "Displays a graph of the top 10 user's WPM over keystrokes for a daily quote",
    "parameters": "[date/day_number]",
}


class DailyGraph(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def dailygraph(self, ctx: commands.Context, *args: str):
        arg = "".join(args)
        try:
            number = int(arg)
            daily_quote = await get_daily_quote(number=number, get_keystrokes=True)
        except ValueError:
            date = parse_date("".join(args))
            daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"), results=10, get_keystrokes=True)

        await run(ctx, daily_quote, )


async def run(ctx: commands.Context, daily_quote: dict):
    quote = get_quote(daily_quote["quote"]["quoteId"])
    set_recent_quote(ctx.channel.id, quote["quoteId"])
    score_list = []
    themed_line = 0

    for i, score in enumerate(daily_quote["leaderboard"][:10]):
        keystroke_data = get_keystroke_data(score["keystrokeData"])
        score["keystroke_wpm"] = keystroke_data["keystroke_wpm"]
        score_list.append(score)

        if score["userId"] == ctx.user["userId"]:
            themed_line = i

    title = (
        f"Daily Quote #{daily_quote["dayNumber"]:,} - "
        f"{format_date(parse_date(daily_quote["startDate"]))}\n"
        f"{quote["quoteId"]}"
    )

    page = Page(
        title=title,
        description=daily_quote_display(daily_quote),
        render=lambda: daily_graph.render(
            score_list,
            title.split("\n")[0],
            ctx.user["theme"],
            themed_line,
        )
    )

    message = Message(
        ctx, page,
        url=race_url(quote["quoteId"])
    )

    await message.send()
