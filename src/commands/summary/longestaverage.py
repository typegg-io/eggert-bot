from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.summary.races import build_stat_fields
from database.typegg.races import get_races
from utils.errors import BotError, MissingArguments, NoRaces
from utils.messages import Page, Message

info = {
    "name": "longestaverage",
    "aliases": ["la"],
    "description": "Displays the longest streak of consecutive races a user maintained a given WPM average.",
    "parameters": "[username] <wpm>",
    "examples": [
        "-la 150",
        "-la eiko 150",
    ],
}


class LongestAverage(Command):
    supported_flags = {"raw", "gamemode", "status", "language", "number"}

    @commands.command(aliases=info["aliases"])
    async def longestaverage(self, ctx: BotContext, *args: str):
        ctx.flags.gamemode = ctx.flags.gamemode or "quickplay"

        if ctx.flags.number is None:
            raise MissingArguments

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, abs(ctx.flags.number))


def get_longest_average(values, threshold):
    """
    Find the longest contiguous subarray whose average is at
    least threshold, using prefix sums and a monotonic stack.
    """
    adjusted = [v - threshold for v in values]

    prefix = [0]
    for val in adjusted:
        prefix.append(prefix[-1] + val)

    stack = []
    for i, val in enumerate(prefix):
        if not stack or val < prefix[stack[-1]]:
            stack.append(i)

    max_len = 0
    best_start = None
    best_end = None

    for j in reversed(range(len(prefix))):
        while stack and prefix[j] >= prefix[stack[-1]]:
            i = stack.pop()
            length = j - i

            if length > max_len:
                max_len = length
                best_start = i
                best_end = j - 1

    if max_len == 0:
        return None

    return best_start, best_end, max_len


def top_10_longest_averages(values, threshold):
    """Repeatedly find and remove the longest average streak to collect up to 10 non-overlapping results."""
    remaining = values[:]
    offset_map = list(range(len(values)))
    results = []

    for _ in range(10):
        streak = get_longest_average(remaining, threshold)
        if not streak:
            break

        start, end, length = streak

        orig_start = offset_map[start]
        orig_end = offset_map[end]

        window = values[orig_start:orig_end + 1]
        average = sum(window) / len(window)

        results.append({
            "start": orig_start,
            "end": orig_end,
            "length": length,
            "average": average,
        })

        used = set(range(start, end + 1))

        new_remaining = []
        new_offset_map = []

        for i, val in enumerate(remaining):
            if i not in used:
                new_remaining.append(val)
                new_offset_map.append(offset_map[i])

        remaining = new_remaining
        offset_map = new_offset_map

    return results


async def run(ctx: BotContext, profile: dict, wpm: float):
    race_list = await get_races(
        user_id=profile["userId"],
        flags=ctx.flags,
    )

    if not race_list:
        raise NoRaces(profile["username"])

    values = [race["wpm"] for race in race_list]
    longest = get_longest_average(values, wpm)

    if not longest:
        raise BotError(
            "No Streak Found",
            "User has no average streak above this WPM"
        )

    start, end, length = longest
    streak_races = race_list[start:end + 1]

    longest_averages = top_10_longest_averages(values, wpm)
    longest_averages.sort(key=lambda x: (-x["length"], -x["average"]))

    fields = build_stat_fields(profile, streak_races, ctx.flags)

    pages = [Page(
        title=f"Longest Average of {wpm:,.2f} WPM+",
        description=(
            f"**{length:,}** races "
            f"(#{streak_races[0]['raceNumber']:,} "
            f"– #{streak_races[-1]['raceNumber']:,})"
        ),
        fields=fields,
        button_name="Longest Average",
        flag_title=True,
    )]

    top_10 = ""

    for i, streak in enumerate(longest_averages, start=1):
        top_10 += (
            f"{i}. **{streak["length"]:,}** races - "
            f"{streak["average"]:,.2f} WPM ("
            f"#{race_list[streak["start"]]['raceNumber']:,} "
            f"– #{race_list[streak["end"]]['raceNumber']:,})\n"
        )

    pages.append(Page(
        title="Top 10 Longest Streaks",
        description=top_10,
        button_name="Top 10 Longest",
        flag_title=True,
    ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
