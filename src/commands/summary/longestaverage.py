from typing import Optional

from discord.ext import commands

from commands.base import Command
from commands.summary.races import build_stat_fields
from database.typegg.races import get_races
from utils.errors import GeneralException
from utils.messages import Page, Message
from utils.strings import parse_number, get_flag_title

info = {
    "name": "longestaverage",
    "aliases": ["la"],
    "description": "Displays the longest number of races a user has maintained a WPM average",
    "parameters": "<username> <wpm>",
}


class LongestAverage(Command):
    @commands.command(aliases=info["aliases"])
    async def longestaverage(self, ctx, username: Optional[str] = "me", wpm: Optional[str] = None):
        if wpm is None:
            try:
                parse_number(username)
                wpm, username = username, "me"
            except (ValueError, TypeError):
                return await ctx.send("Please provide a WPM threshold.")

        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        await run(ctx, profile, parse_number(wpm))


def get_longest_average(values, threshold):
    """Find the longest contiguous subarray whose average is at least threshold, using prefix sums and a monotonic stack."""
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


async def run(ctx: commands.Context, profile: dict, wpm: float):
    ctx.flags.gamemode = ctx.flags.gamemode or "quickplay"
    race_list = await get_races(
        user_id=profile["userId"],
        flags=ctx.flags,
    )

    if not race_list:
        return await ctx.send("No races found.")

    values = [race["wpm"] for race in race_list]
    longest = get_longest_average(values, wpm)

    if not longest:
        raise GeneralException(
            "No Streak Found",
            "User has no average streak above this WPM"
        )

    start, end, length = longest
    streak_races = race_list[start:end + 1]

    longest_averages = top_10_longest_averages(values, wpm)
    longest_averages.sort(key=lambda x: (-x["length"], -x["average"]))

    fields = build_stat_fields(profile, streak_races, ctx.flags)

    pages = [Page(
        title=f"Longest Average of {wpm:,.2f} WPM+" + get_flag_title(ctx.flags),
        description=(
            f"**{length:,}** races "
            f"(#{streak_races[0]['raceNumber']:,} "
            f"– #{streak_races[-1]['raceNumber']:,})"
        ),
        fields=fields,
        button_name="Longest Average"
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
        title="Top 10 Longest Streaks" + get_flag_title(ctx.flags),
        description=top_10,
        button_name="Top 10 Longest",
    ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
