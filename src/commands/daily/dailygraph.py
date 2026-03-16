from discord.ext import commands

from api.daily_quotes import get_daily_quote
from commands.base import Command
from commands.daily.dailyleaderboard import daily_quote_display
from config import DAILY_QUOTE_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote
from database.typegg.quotes import get_quote
from graphs import daily as daily_graph
from utils.dates import parse_date, format_date
from utils.errors import GeneralException
from utils.keystrokes import get_keystroke_data
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
            daily_quote = await get_daily_quote(number=number, results=100, get_keystrokes=True)
        except ValueError:
            date = parse_date("".join(args))
            daily_quote = await get_daily_quote(date.strftime("%Y-%m-%d"), results=100, get_keystrokes=True)

        await run(ctx, daily_quote)


async def run(ctx: commands.Context, daily_quote: dict):
    quote = get_quote(daily_quote["quote"]["quoteId"])
    set_recent_quote(ctx.channel.id, quote["quoteId"])
    leaderboard = daily_quote.get("leaderboard") or []

    if not leaderboard:
        raise GeneralException("No Results", "No daily scores to display")

    def build_score_list(entries):
        scores = []
        for score in entries:
            score = dict(score)
            score["keystroke_wpm"] = get_keystroke_data(score["keystrokeData"]).keystrokeWpm
            scores.append(score)
        return scores

    title = (
        f"Daily Quote #{daily_quote["dayNumber"]:,} - "
        f"{format_date(parse_date(daily_quote["startDate"]))}\n"
        f"{quote["quoteId"]}"
    )
    description = daily_quote_display(daily_quote)
    graph_title = title.split("\n")[0]

    user_index = next(
        (i for i, s in enumerate(leaderboard) if s["userId"] == ctx.user["userId"]),
        None,
    )

    top10_scores = build_score_list(leaderboard[:10])
    top10_themed = user_index if user_index is not None and user_index < 10 else 0

    page = Page(
        title=title,
        description=description,
        button_name="Top 10" if user_index is not None else None,
        default=True,
        render=lambda: daily_graph.render(
            top10_scores,
            graph_title,
            ctx.user["theme"],
            top10_themed,
        ),
    )

    pages = [page]

    if user_index is not None:
        start = max(0, user_index - 4)
        end = start + 10
        if end > len(leaderboard):
            end = len(leaderboard)
            start = max(0, end - 10)
        window_scores = build_score_list(leaderboard[start:end])
        window_themed = user_index - start

        pages.append(Page(
            title=title,
            description=description,
            button_name="My Position",
            render=lambda: daily_graph.render(
                window_scores,
                graph_title,
                ctx.user["theme"],
                window_themed,
            ),
        ))

    message = Message(ctx, pages=pages, url=race_url(quote["quoteId"]))
    await message.send()
