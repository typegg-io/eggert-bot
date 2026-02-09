from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.errors import NumberGreaterThan
from utils.messages import Message, Field, Page
from utils.strings import get_flag_title, format_duration

info = {
    "name": "average",
    "aliases": ["avg", "a", "rsa", "rawsa"],
    "description": "Displays the average stats of a user's last n races\n"
                   "`n` defaults to 25",
    "parameters": "[user_id] [n]",
}


class Average(Command):
    @commands.command(aliases=info["aliases"])
    async def average(self, ctx, username: Optional[str] = "me", n: Optional[int] = 25):
        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        await run(ctx, profile, n)


async def run(ctx: commands.Context, profile: dict, n: int):

    if n < 1:
        raise NumberGreaterThan

    race_list = await get_races(
        profile["userId"],
        reverse=True,
        flags=ctx.flags,
        limit=n,
    )
    quote_list = get_quotes()
    multiplayer = ctx.flags.gamemode in ["quickplay", "lobby"]
    n = min(n, len(race_list))
    dnf_count = 0

    stats = {
        "pp": 0, "wpm": 0, "accuracy": 0, "duration": 0, "difficulty": 0,
        "rawPp": 0, "rawWpm": 0, "flow": 0, "errorReactionTime": 0, "errorRecoveryTime": 0,
    }
    dnf_stats = {"pp", "wpm", "rawPp", "rawWpm"}

    for race in race_list:
        race = dict(race)
        if multiplayer and race.get("completionType") in ["quit", "dnf"]:
            dnf_count += 1
        for key in stats:
            if key == "difficulty":
                stats[key] += quote_list[race["quoteId"]]["difficulty"]
            elif key == "flow":
                stats[key] += 0 if race["wpm"] == 0 else race["wpm"] / race["rawWpm"]
            elif key == "rawPp" and multiplayer:
                stats[key] += 0 if race["wpm"] == 0 else race["pp"] * (race["rawWpm"] / race["wpm"])
            elif key in race:
                stats[key] += race[key] or 0

    for key in stats:
        if key in dnf_stats or not multiplayer:
            stats[key] /= n
        else:
            stats[key] /= (n - dnf_count)

    page = Page(
        title=f"Average Stats - Last {n:,} Races" + get_flag_title(ctx.flags),
        fields=[
            Field(
                title="Stats",
                content=(
                    f"**Score:** {stats["pp"]:,.2f} pp\n"
                    f"**Speed:** {stats["wpm"]:,.2f} WPM\n"
                    f"**Accuracy:** {stats["accuracy"]:.2%}\n"
                    f"**Race Time:** {format_duration(stats["duration"] / 1000, round_seconds=False)}\n"
                    f"**Difficulty:** {stats["difficulty"]:,.2f}★"
                ),
                inline=True,
            ),
            Field(
                title="Raw Stats",
                content=(
                    f"**Score:** {stats["rawPp"]:,.2f} pp\n"
                    f"**Speed:** {stats["rawWpm"]:,.2f} WPM\n"
                    f"**Flow:** {stats["flow"]:.2%}\n"
                    f"**Error Reaction:** {stats["errorReactionTime"]:,.0f}ms\n"
                    f"**Error Recovery:** {stats["errorRecoveryTime"]:,.0f}ms"
                ),
                inline=True,
            )
        ]
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
