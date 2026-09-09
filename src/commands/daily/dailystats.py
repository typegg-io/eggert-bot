from collections import defaultdict

import numpy as np
from discord.ext import commands

from api.daily_quotes import START_DATE
from command_info import CommandInfo
from commands.base import Command
from config import DAILY_QUOTE_CHANNEL_ID
from context import BotContext
from database.typegg.daily_quotes import get_daily_quote_id, get_today_result, get_user_results
from utils import dates
from utils.messages import Field, Message, Page, usable_in
from utils.schemas import Profile
from utils.strings import get_streak_emoji, pp_display

info = CommandInfo(
    name="dailystats",
    aliases=["ds"],
    description="Displays stats about a user's daily quote history.\n"
                "Includes streaks, participation rate, average pp/WPM, and top placements.",
    parameters="[username]",
    examples=[
        "-ds",
        "-ds joshu",
    ],
)


class DailyStats(Command):
    """Display a user's daily quote history."""

    supported_flags = {"raw"}

    @commands.command(aliases=info.aliases)
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def dailystats(self, ctx: BotContext, username: str = None):
        """Resolve the username, then render their daily quote stats."""
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's daily streaks, participation rate, averages and placements."""
    daily_stats = profile["stats"]["dailyQuotes"]
    streak = daily_stats["streak"]
    results = get_user_results(profile["userId"])

    if not results:
        message = Message(
            ctx,
            title="Daily Quote Stats",
            page=Page(
                description="User has not participated in any finished daily quotes."
            ),
            profile=profile,
        )
        return await message.send()

    total_days = (dates.now() - START_DATE).days + 1
    total_days = min(total_days, (dates.now() - dates.parse_date(profile["joinDate"])).days + 2)

    today_quote_id = get_daily_quote_id()
    today_result = get_today_result(profile["userId"], today_quote_id, ctx.flags.raw) if today_quote_id else None

    pp_key, wpm_key = ("rawPp", "rawWpm") if ctx.flags.raw else ("pp", "wpm")
    hide_raw_pp = ctx.flags.raw and not ctx.user["isGgPlus"]
    pp, wpm, positions = zip(*[(race[pp_key], race[wpm_key], race["rank"]) for race in results])
    pp = list(pp)
    wpm = list(wpm)

    if today_result:
        pp.append(today_result["pp"])
        wpm.append(today_result["wpm"])

    # Excluding 0 pp values
    ranked_pp = [p for p in pp if p > 0]
    average_pp = np.average(ranked_pp) if ranked_pp else 0

    fields = [
        Field(
            title="Participation",
            content=(
                f"**Current Streak:** {streak:,}{get_streak_emoji(streak)}\n"
                f"**Best Streak:** {daily_stats["bestStreak"]:,}\n"
                f"**Total Completed:** {daily_stats["completed"]:,}\n"
                f"**Participation Rate:** {daily_stats["completed"] / total_days:,.2%}\n\n"
            ),
        ),
        Field(
            title="Stats",
            content=(
                f"**Average Performance:** {pp_display(average_pp, hide_raw_pp)}\n"
                f"**Best Performance:** {pp_display(max(pp), hide_raw_pp)}\n"
                f"**Average Speed:** {np.average(wpm):,.2f} WPM\n"
                f"**Best Speed:** {max(wpm):,.2f} WPM\n"
            ),
        )
    ]

    ranks = defaultdict(int)
    for row in results:
        ranks[row["rank"]] += 1
    top_10s = sum(ranks[rank] for rank in range(1, 11))

    fields.append(Field(
        title="Placements",
        content=(
            (f":trophy: **Champion:** {ranks[1]:,}\n" if ranks[1] else "") +
            (f":medal: **Runner-up:** {ranks[2]:,}\n" if ranks[2] else "") +
            (f":third_place: **Third Place:** {ranks[3]:,}\n" if ranks[3] else "") +
            (f":star: **Top 10:** {top_10s:,}\n" if top_10s > 0 else "") +
            f":bar_chart: **Median Rank:** {np.median(positions):,.0f}"
        )
    ))

    page = Page(
        title="Daily Quote Stats" + (" (Raw)" if ctx.flags.raw else ""),
        fields=fields,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
