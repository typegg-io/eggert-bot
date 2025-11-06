from typing import Optional

from discord.ext import commands

from api.users import get_race
from commands.base import Command
from database.typegg.quotes import get_quote
from graphs import race as race_graph
from utils.keylogs import get_keystroke_data
from utils.messages import Page, Message, Field
from utils.strings import quote_display, discord_date, format_duration

info = {
    "name": "racegraph",
    "aliases": ["rg", "r"],
    "description": "Displays a graph of a user's WPM over keystrokes for a given race",
    "parameters": "[username] [number]",
}


class RaceGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def racegraph(self, ctx, username: Optional[str] = "me", race_number: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        race_number = self.get_race_number(profile, race_number)

        await run(ctx, profile, race_number)


async def run(ctx: commands.Context, profile: dict, race_number: int):
    race = await get_race(profile["userId"], race_number, get_keystrokes=True)
    quote = get_quote(race["quoteId"])
    keystroke_data = get_keystroke_data(race["keystrokeData"])

    description = (
        f"Completed {discord_date(race["timestamp"])}\n\n"
        f"{quote_display(quote, 1000, display_status=True)}"
    )

    title = f"Race Graph - Race #{race_number:,}"
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
                    f"**Score:** {race["rawPp"]:,.2f} pp\n"
                    f"**Speed:** {race["rawWpm"]:,.2f} WPM\n"
                    f"**Error Reaction:** {race["errorReactionTime"]:,.0f}ms\n"
                    f"**Error Recovery:** {race["errorRecoveryTime"]:,.0f}ms"
                ),
                inline=True,
            ),
        ],
        render=lambda: race_graph.render(
            keystroke_data["keystroke_wpm"],
            keystroke_data["keystroke_wpm_raw"],
            keystroke_data["typos"],
            profile["username"],
            title,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
