from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.errors import AllQuits, NoRacesFiltered, NumberGreaterThan
from utils.flags import is_multiplayer
from utils.messages import Field, Message, Page
from utils.schemas import Profile
from utils.strings import format_duration, pp_display

info = CommandInfo(
    name="average",
    aliases=["avg", "a", "rsa", "rawsa"],
    description="Displays the average stats of a user's last n races.",
    parameters="[username] [n:25]",
    examples=[
        "-a",
        "-a eiko",
        "-a eiko 50",
    ],
)


class Average(Command):
    """Display the average stats of a user's last n races."""

    supported_flags = {"gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def average(self, ctx: BotContext, *args: str):
        """Default to the last 25 quickplay races, then average them."""
        ctx.flags.gamemode = ctx.flags.gamemode or "quickplay"
        n = int(abs(ctx.flags.number)) if ctx.flags.number is not None else 25
        profile = await self.get_profile(ctx, args[0] if args else None)

        await run(ctx, profile, n)


async def run(ctx: BotContext, profile: Profile, n: int) -> None:
    """Send the averaged speed, accuracy and difficulty of a user's last n races."""
    if n < 1:
        raise NumberGreaterThan

    race_list = await get_races(
        profile["userId"],
        reverse=True,
        flags=ctx.flags,
        limit=n,
    )
    if not race_list:
        raise NoRacesFiltered(profile["username"])

    quote_list = get_quotes()
    multiplayer = is_multiplayer(ctx.flags)
    n = min(n, len(race_list))
    dnf_count = 0

    stats = {
        "pp": 0, "wpm": 0, "accuracy": 0, "duration": 0, "difficulty": 0,
        "rawPp": 0, "rawWpm": 0, "flow": 0, "errorReactionTime": 0, "errorRecoveryTime": 0,
    }
    dnf_stats = {"pp", "wpm", "rawPp", "rawWpm", "difficulty"}

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

    if dnf_count == n:
        raise AllQuits

    for key in stats:
        if key in dnf_stats or not multiplayer:
            stats[key] /= n
        else:
            stats[key] /= (n - dnf_count)

    raw_pp_display = pp_display(stats["rawPp"], not ctx.user["isGgPlus"])

    page = Page(
        title=f"Average Stats - Last {n:,} Races",
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
                    f"**Score:** {raw_pp_display}\n"
                    f"**Speed:** {stats["rawWpm"]:,.2f} WPM\n"
                    f"**Flow:** {stats["flow"]:.2%}\n"
                    f"**Error Reaction:** {stats["errorReactionTime"]:,.0f}ms\n"
                    f"**Error Recovery:** {stats["errorRecoveryTime"]:,.0f}ms"
                ),
                inline=True,
            )
        ],
        flag_title=True,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
