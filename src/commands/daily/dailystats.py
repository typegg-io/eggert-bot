from collections import defaultdict

import numpy as np
from discord.ext import commands

from api.daily_quotes import START_DATE
from bot_setup import BotContext
from commands.base import Command
from config import DAILY_QUOTE_CHANNEL_ID
from database.typegg.daily_quotes import get_user_results, get_today_result, get_daily_quote_id
from utils import dates
from utils.messages import Page, Message, Field, usable_in
from utils.strings import get_streak_emoji

info = {
    "name": "dailystats",
    "aliases": ["ds"],
    "description": "Displays stats about a user's daily quote history.\n"
                   "Includes streaks, participation rate, average pp/WPM, and top placements.",
    "parameters": "[username]",
    "examples": [
        "-ds",
        "-ds joshu",
    ],
}


class DailyStats(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(DAILY_QUOTE_CHANNEL_ID)
    async def dailystats(self, ctx: BotContext, username: str = None):
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: dict):
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
    today_result = get_today_result(profile["userId"], today_quote_id) if today_quote_id else None

    pp, wpm, positions = zip(*[(race["pp"], race["wpm"], race["rank"]) for race in results])
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
                f"**Average Performance:** {average_pp:,.2f} pp\n"
                f"**Best Performance:** {max(pp):,.2f} pp\n"
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
        title="Daily Quote Stats",
        fields=fields,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
