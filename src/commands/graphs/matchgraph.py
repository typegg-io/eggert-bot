from copy import deepcopy
from typing import Optional

from discord.ext import commands

from api.users import get_race
from commands.base import Command
from commands.graphs.racegraph import run as run_racegraph
from database.typegg.quotes import get_quote
from graphs import match as match_graph
from utils.errors import InvalidKeystrokeData
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message
from utils.stats import get_pauseless_delays
from utils.strings import quote_display, discord_date, rank, username_with_flag

info = {
    "name": "matchgraph",
    "aliases": ["mg"],
    "description": "Displays multiplayer rankings and a graph of each user's WPM over keystrokes",
    "parameters": "[username] [number]",
}


class MatchGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def matchgraph(self, ctx, username: Optional[str] = "me", race_number: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=True)
        race_number = await self.get_race_number(profile, race_number)

        await run(ctx, profile, race_number)


async def run(ctx: commands.Context, profile: dict, race_number: int):
    race = await get_race(profile["userId"], race_number, get_keystrokes=True)
    match = race.get("match")

    if not match:
        return await run_racegraph(ctx, profile, race_number)

    quote = get_quote(race["quoteId"])
    themed_line = 0
    raw_themed_line = 0

    description = (
        f"Completed {discord_date(race["timestamp"])}\n\n"
        f"{quote_display(quote, 1000, display_status=True)}\n"
        f"**Rankings**\n"
    )

    raw_description = (
        f"Completed {discord_date(race["timestamp"])}\n\n"
        f"{quote_display(quote, 1000, display_status=True)}\n"
        f"**Raw Rankings**\n"
    )

    players = match["players"]
    players.sort(key=lambda x: -x["matchWpm"])

    raw_players = deepcopy(players)
    raw_players.sort(key=lambda x: -x["rawMatchWpm"])

    for i, player in enumerate(players):
        if player["userId"] == ctx.user["userId"]:
            themed_line = i

        bot = ":robot:" if player["botId"] else ""
        try:
            keystroke_data = get_keystroke_data(player["keystrokeData"])
        except InvalidKeystrokeData:
            continue

        players[i].update({"keystroke_wpm": keystroke_data.keystrokeWpm})

        description += (
            f"{rank(i + 1)} {bot} {username_with_flag(player, False)} - "
            f"{player["matchWpm"]:,.2f} WPM ({player["accuracy"]:.2%} Acc, "
            f"{player["startTime"]:,.0f}ms Start)\n"
        )

    for i, player in enumerate(raw_players):
        if player["userId"] == ctx.user["userId"]:
            raw_themed_line = i

        bot = ":robot:" if player["botId"] else ""
        try:
            keystroke_data = get_keystroke_data(player["keystrokeData"])
        except InvalidKeystrokeData:
            continue
        flow = player["matchWpm"] / player["rawMatchWpm"]
        raw_delays = keystroke_data.rawCharacterTimes
        pauseless_delays = get_pauseless_delays(raw_delays)
        pause_percent = 1 - (sum(pauseless_delays) / sum(raw_delays))

        raw_players[i].update({"keystroke_wpm": keystroke_data.keystrokeRawWpm})

        raw_description += (
            f"{rank(i + 1)} {bot} {username_with_flag(player, False)} - "
            f"{player["rawMatchWpm"]:,.2f} WPM ({flow:.2%} Flow, "
            f"{pause_percent:.2%} Pause)\n"
        )

    players = [player for player in players if player.get("keystroke_wpm")]
    raw_players = [player for player in raw_players if player.get("keystroke_wpm")]

    title = f"Match Graph - Race #{race_number:,}"

    page = Page(
        title=title,
        description=description,
        render=lambda: match_graph.render(
            players,
            title,
            ctx.user["theme"],
            themed_line=themed_line,
        ),
        button_name="Rankings",
    )

    raw_page = Page(
        title=title,
        description=raw_description,
        render=lambda: match_graph.render(
            raw_players,
            title,
            ctx.user["theme"],
            themed_line=raw_themed_line,
        ),
        button_name="Raw Rankings",
    )

    message = Message(
        ctx,
        pages=[page, raw_page],
        profile=profile,
    )

    await message.send()
