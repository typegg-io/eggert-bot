from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, enforce_daily_quote
from commands.daily.dailygraph import send_leaderboard_graph
from commands.quotes.quoteleaderboard import quote_leaderboard_display
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.bot.recent_quotes import get_recent_quote
from utils.errors import BotError, MissingArguments
from utils.messages import usable_in
from utils.urls import race_url

info = CommandInfo(
    name="topgraph",
    aliases=["10g", "tg"],
    description="Displays a WPM over keystrokes graph for the top 10 on a quote's leaderboard.\n"
                "My Position graphs the 10 around you, if you place in the top 100.",
    parameters="<quote_id>",
    examples=[
        "-10g piykyai_3408",
        "-10g piykyai_3408 raw",
    ],
)


class TopGraph(Command):
    """Graph WPM over keystrokes for the top 10 on one quote."""

    supported_flags = {"raw", "quote_id"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def topgraph(self, ctx: BotContext):
        """Resolve the quote from the flag or the channel's most recent one, then graph it."""
        if ctx.flags.quote_id is None:
            ctx.flags.quote_id = get_recent_quote(ctx.channel.id)
            if ctx.flags.quote_id is None:
                raise MissingArguments
        quote = await self.get_quote(ctx, ctx.flags.quote_id, from_api=True, results=100)
        enforce_daily_quote(ctx, quote["quoteId"])
        await run(ctx, quote)


async def run(ctx: BotContext, quote: dict) -> None:
    """Send the top 10 graph for a quote, plus a page centred on the caller when they placed."""
    if not quote["leaderboard"]:
        raise BotError("No Results", "No one has raced this quote")

    await send_leaderboard_graph(
        ctx,
        quote["leaderboard"],
        title=quote["quoteId"],
        description=quote_leaderboard_display(quote),
        graph_title=("Raw " if ctx.flags.raw else "") + f"Quote Leaderboard - {quote["quoteId"]}",
        url=race_url(quote["quoteId"]),
    )
