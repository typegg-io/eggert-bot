from typing import Optional

from discord.ext import commands

from api.daily_quotes import get_daily_quote
from api.users import get_race
from commands.base import Command
from config import DAILY_QUOTE_CHANNEL_ID
from database.bot.recent_quotes import set_recent_quote
from database.typegg.quotes import get_quote
from database.typegg.users import get_quote_bests
from graphs import race as race_graph
from utils.errors import NoQuoteRaces, DailyQuoteChannel
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message, Field, usable_in
from utils.strings import quote_display, discord_date, format_duration, GG_PLUS, GG_PLUS_LINK

info = {
    "name": "racegraph",
    "aliases": ["rg", "r"],
    "description": "Displays a graph of a user's WPM over keystrokes for a given race.\n"
                   "Passing a quote ID will show the user's best race for that quote.",
    "parameters": "[username] [number/quote_id]",
}


class RaceGraph(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def racegraph(self, ctx, username: Optional[str] = "me", race_identifier: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        try:
            race_number = await self.get_race_number(profile, race_identifier)
        except Exception:
            quote = await self.get_quote(ctx, race_identifier, profile["userId"])
            quote_bests = get_quote_bests(profile["userId"], quote_id=quote["quoteId"])
            if not quote_bests:
                raise NoQuoteRaces(profile["username"])
            race_number = quote_bests[0]["raceNumber"]

        await run(ctx, profile, race_number)


async def run(ctx: commands.Context, profile: dict, race_number: int):
    race = await get_race(profile["userId"], race_number, get_keystrokes=True)
    quote = get_quote(race["quoteId"])

    if ctx.channel.id == DAILY_QUOTE_CHANNEL_ID:
        daily_data = await get_daily_quote(results=1)
        if race["quoteId"] != daily_data["quote"]["quoteId"]:
            raise DailyQuoteChannel

    keystroke_data = get_keystroke_data(race["keystrokeData"])
    set_recent_quote(ctx.channel.id, race["quoteId"])

    description = (
        f"Completed {discord_date(race["timestamp"])}\n\n"
        f"{quote_display(quote, 1000, display_status=True)}"
    )

    title = f"Race Graph - Race #{race_number:,}"
    raw_pp_display = (
        f"{race["rawPp"]:,.2f} pp" if ctx.user["isGgPlus"]
        else f"[{GG_PLUS}]({GG_PLUS_LINK})"
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
