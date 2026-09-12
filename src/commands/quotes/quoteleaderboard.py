from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, enforce_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.bot.recent_quotes import get_recent_quote
from utils.dates import discord_date
from utils.errors import MissingArguments
from utils.messages import Message, Page, paginate_leaderboard, usable_in
from utils.strings import pp_display, quote_display, rank, username_with_flag
from utils.urls import race_url

info = CommandInfo(
    name="quoteleaderboard",
    aliases=["qlb", "10"],
    description="Displays the top 100 leaderboard for a specific quote.",
    parameters="<quote_id>",
    examples=[
        "-10 piykyai_3408",
    ],
)


class QuoteLeaderboard(Command):
    """Display the top 100 leaderboard for one quote."""

    supported_flags = {"quote_id", "raw"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def quoteleaderboard(self, ctx: BotContext):
        """Resolve the quote from the flag or the channel's most recent one, then render it."""
        if ctx.flags.quote_id is None:
            ctx.flags.quote_id = get_recent_quote(ctx.channel.id)
            if ctx.flags.quote_id is None:
                raise MissingArguments
        quote = await self.get_quote(ctx, ctx.flags.quote_id, from_api=True, results=100)
        enforce_daily_quote(ctx, quote["quoteId"])
        await run(ctx, quote)


async def run(ctx: BotContext, quote: dict) -> None:
    """Send a quote and the fastest race of each of its top 100 users, 10 per page."""
    wpm_key, pp_key = ("rawWpm", "rawPp") if ctx.flags.raw else ("wpm", "pp")
    hide_raw_pp = ctx.flags.raw and not ctx.user["isGgPlus"]

    # The API ranks on wpm, so raw ranks only hold within the 100 entries fetched.
    if ctx.flags.raw:
        quote["leaderboard"].sort(key=lambda score: -score["rawWpm"])

    def format_row(index: int, score: dict) -> str:
        """Format one leaderboard row, bolded when it belongs to the caller."""
        bold = "**" if score["userId"] == ctx.user["userId"] else ""

        rank_display = rank(index + 1)
        if bold:
            rank_display = rank_display.replace("*", "")

        pp = f"{pp_display(score[pp_key], hide_raw_pp, 0)} - " if quote["ranked"] else ""
        return (
            f"{bold}{rank_display} {username_with_flag(score)} - "
            f"{score[wpm_key]:,.2f} WPM ({score["accuracy"]:.2%}) - {pp}"
            f"{discord_date(score["timestamp"])}{bold}\n"
        )

    if quote["leaderboard"]:
        pages, jump_page = paginate_leaderboard(quote["leaderboard"], format_row, ctx.user["userId"])
    else:
        pages, jump_page = [Page(description="No one has raced this quote.")], None

    message = Message(
        ctx,
        title=quote["quoteId"],
        header=quote_leaderboard_display(quote) + f"\n**Leaderboard{" (Raw)" if ctx.flags.raw else ""}**",
        pages=pages,
        url=race_url(quote["quoteId"]),
        thumbnail=quote["source"]["thumbnailUrl"],
        jump_page=jump_page,
        remember=True,
    )

    await message.send()


def quote_leaderboard_display(quote: dict) -> str:
    """Format a quote's text and metadata for the top of its leaderboard."""
    return quote_display(
        quote,
        display_author=True,
        display_status=True,
        display_racers_users=True,
        display_submitted_by=True,
        max_text_chars=1000,
    )
