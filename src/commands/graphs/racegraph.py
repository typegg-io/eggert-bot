from discord.ext import commands

from commands.base import Command, enforce_daily_quote
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.bot.recent_quotes import set_recent_quote
from database.typegg.quotes import get_quote
from database.typegg.races import get_race
from database.typegg.users import get_quote_bests
from graphs import race as race_graph
from utils.dates import discord_date
from utils.errors import NoQuoteRaces
from utils.keystrokes import get_keystroke_data
from utils.messages import Field, Message, Page, usable_in
from utils.strings import GG_PLUS_LINKED, format_duration, quote_display

info = {
    "name": "racegraph",
    "aliases": ["rg", "r"],
    "description": "Displays a WPM over keystrokes graph for a given race.\n"
                   "Pass a quote ID to show the user's best race on that quote.",
    "parameters": "[username] [race_number/quote_id]",
    "examples": [
        "-r",
        "-r eiko",
        "-r eiko 1500",
        "-r eiko piykyai_3408",
    ],
}


class RaceGraph(Command):
    supported_flags = {"number", "quote_id"}

    @commands.command(aliases=info["aliases"])
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def racegraph(self, ctx: BotContext, *args: str):
        ctx.flags.status = None
        profile = await self.get_profile(ctx, args[0] if args else None)

        if ctx.flags.number is not None or ctx.flags.quote_id is None:
            race_number = await self.get_race_number(profile, ctx.flags.number)
        else:
            quote = await self.get_quote(ctx, ctx.flags.quote_id, profile["userId"])
            quote_bests = get_quote_bests(profile["userId"], quote_id=quote["quoteId"], flags=ctx.flags)
            if not quote_bests:
                raise NoQuoteRaces(profile["username"])
            race_number = quote_bests[0]["raceNumber"]

        await run(ctx, profile, race_number)


async def run(ctx: BotContext, profile: dict, race_number: int):
    race = get_race(profile["userId"], race_number, get_keystrokes=True)
    quote = get_quote(race["quoteId"])
    set_recent_quote(ctx.channel.id, race["quoteId"])

    enforce_daily_quote(ctx, race["quoteId"])

    keystroke_data = get_keystroke_data(race["keystrokeData"])

    description = (
        f"Completed {discord_date(race["timestamp"])}\n\n"
        f"{quote_display(quote, 1000, display_status=True)}"
    )

    title = f"Race Graph - Race #{race_number:,}"
    raw_pp_display = (
        f"{race["rawPp"]:,.2f} pp" if ctx.user["isGgPlus"]
        else GG_PLUS_LINKED
    )

    page = Page(
        title=title,
        description=description,
        fields=[
            Field(
                title="Stats",
                content=(
                    f"**Score:** {race["pp"]:,.2f} pp\n"
                    f"**Speed:** {race["wpm"]:,.2f} WPM\n"
                    f"**Accuracy:** {race["accuracy"]:.2%}\n"
                    f"**Race Time:** {format_duration(race["duration"] / 1000, round_seconds=False)}"
                ),
                inline=True,
            ),
            Field(
                title="Raw Stats",
                content=(
                    f"**Score:** {raw_pp_display}\n"
                    f"**Speed:** {race["rawWpm"]:,.2f} WPM\n"
                    f"**Error Reaction:** {race["errorReactionTime"]:,.0f}ms\n"
                    f"**Error Recovery:** {race["errorRecoveryTime"]:,.0f}ms"
                ),
                inline=True,
            ),
        ],
        render=lambda: race_graph.render(
            keystroke_data.keystrokeWpm,
            keystroke_data.keystrokeRawWpm,
            keystroke_data.typos,
            profile["username"],
            title,
            ctx.user["theme"],
        ),
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
