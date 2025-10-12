from collections import defaultdict
from typing import Optional

import numpy as np
from discord.ext import commands

from api.daily_quotes import START_DATE
from commands.base import Command
from database.typegg.daily_quotes import get_user_results
from utils import dates
from utils.messages import Page, Message, Field

info = {
    "name": "dailystats",
    "aliases": ["ds"],
    "description": "Displays daily quote stats for a given user.",
    "parameters": "[username]",
}


class DailyStats(Command):
    @commands.command(aliases=info["aliases"])
    async def dailystats(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username)

        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    daily_stats = profile["stats"]["dailyQuotes"]
    streak = daily_stats["streak"]
    best_streak = daily_stats["bestStreak"]
    fire = " :fire:" if streak > 0 else ""

    if best_streak < 1:
        message = Message(
            ctx,
            title="Daily Quote Stats",
            page=Page(
                description="User has not participated in any daily quotes."
            ),
            profile=profile,
        )
        return await message.send()

    results = get_user_results(profile["userId"])
    total_days = (dates.now() - START_DATE).days + 1
    pp, wpm, positions = zip(*[(race["pp"], race["wpm"], race["rank"]) for race in results])

    fields = [
        Field(
            title="Participation",
            content=(
                f"**Current Streak:** {streak:,}{fire}\n"
                f"**Best Streak:** {daily_stats["bestStreak"]:,}\n"
                f"**Total Completed:** {daily_stats["completed"]:,}\n"
                f"**Completion Rate:** {daily_stats["completed"] / total_days:,.2%}\n\n"
            ),
        ),
        Field(
            title="Stats",
            content=(
                f"**Average Performance:** {np.average(pp):,.2f} pp\n"
                f"**Best Performance:** {max(pp):,.2f} pp\n"
                f"**Average Speed:** {np.average(wpm):,.2f} WPM\n"
                f"**Best Speed:** {max(wpm):,.2f} WPM\n"
                f"**Average Rank:** {np.average(positions):,.2f}"
            ),
        )
    ]

    ranks = defaultdict(int)
    for row in results:
        ranks[row["rank"]] += 1
    top_10s = sum(ranks[rank] for rank in range(1, 11))

    if top_10s > 0:
        fields.append(Field(
            title="Finishes",
            content=(
                (f":trophy: **Champion:** {ranks[1]:,}\n" if ranks[1] else "") +
                (f":medal: **Runner-up:** {ranks[2]:,}\n" if ranks[2] else "") +
                (f":third_place: **Third Place:** {ranks[3]:,}\n" if ranks[3] else "") +
                f":star: **Top 10 Placements:** {top_10s:,}"
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
