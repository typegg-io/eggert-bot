from copy import deepcopy

from discord.ext import commands

from api.users import get_race
from bot_setup import BotContext
from commands.base import Command
from commands.graphs.racegraph import run as run_racegraph
from database.bot.recent_quotes import set_recent_quote
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
    "description": "Displays rankings and WPM over keystrokes for a multiplayer match.\n"
                   "Defaults to the user's most recent match.",
    "parameters": "[username] [race_number]",
    "examples": [
        "-mg",
        "-mg eiko",
        "-mg eiko 1500",
    ],
}


class MatchGraph(Command):
    supported_flags = {"number"}

    @commands.command(aliases=info["aliases"])
    async def matchgraph(self, ctx: BotContext, username: str = None):
        profile = await self.get_profile(ctx, username)
        race_number = await self.get_race_number(profile, int(ctx.flags.number))

        await run(ctx, profile, race_number)


async def run(ctx: BotContext, profile: dict, race_number: int):
    race = await get_race(profile["userId"], race_number, get_keystrokes=True)
    set_recent_quote(ctx.channel.id, race["quoteId"])
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

        if player.get("keystrokeData"):
            try:
                keystroke_data = get_keystroke_data(player["keystrokeData"], True, player["startTime"])
            except InvalidKeystrokeData:
                continue

            players[i].update({"keystroke_wpm": keystroke_data.keystrokeWpm})

            description += (
                f"{rank(i + 1)} {bot} {username_with_flag(player, False)} - "
                f"{player["matchWpm"]:,.2f} WPM ({player["accuracy"]:.2%} Acc, "
                f"{player["startTime"]:,.0f}ms Start)\n"
            )
        else:
            description += f":x: {bot} {username_with_flag(player, False)} - DNF"

    for i, player in enumerate(raw_players):
        if player["userId"] == ctx.user["userId"]:
            raw_themed_line = i

        bot = ":robot:" if player["botId"] else ""

        if player.get("keystrokeData"):
            try:
                keystroke_data = get_keystroke_data(player["keystrokeData"], True, player["startTime"])
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
        else:
            raw_description += f":x: {bot} {username_with_flag(player, False)} - DNF"

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
