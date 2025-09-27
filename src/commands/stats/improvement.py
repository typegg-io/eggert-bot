from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.races import get_races
from graphs import improvement
from utils.errors import invalid_argument
from utils.messages import Page, Message
from utils.strings import get_option

metrics = ["pp", "wpm"]
info = {
    "name": "improvement",
    "aliases": ["imp"],
    "description": "Displays a graph of a user's pp/WPM over races\n"
                   "\\- `metric` defaults to pp",
    "parameters": "[username] [pp|wpm]",
}


class Improvement(Command):
    @commands.command(aliases=info["aliases"])
    async def improvement(self, ctx, username: Optional[str] = "me", metric: Optional[str] = "pp"):
        metric = get_option(metrics, metric)
        if not metric:
            return await ctx.send(embed=invalid_argument(metrics))

        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)
        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str):
    race_list = await get_races(
        profile["userId"],
        columns=[metric, "timestamp"],
        min_pp=0.01,
    )
    value_list, date_list = zip(*[(race[metric], race["timestamp"]) for race in race_list])

    if metric == "wpm":
        metric = metric.upper()

    race_count = len(value_list)
    window_size = min(max(race_count // 15, 1), 500)
    average = np.mean(value_list)
    best = max(value_list)
    worst = min(value_list)
    recent_average = np.mean(value_list[-window_size:])

    description = (
        f"**Races:** {race_count:,}\n"
        f"**Average:** {average:,.2f} {metric}\n"
        f"**Best:** {best:,.2f} {metric}\n"
        f"**Worst:** {worst:,.2f} {metric}\n"
        f"**Average of Last {window_size}:** {recent_average:,.2f} {metric}\n"
    )

    def render(dates=None):
        return lambda: improvement.render(
            values=value_list,
            metric=metric,
            theme=ctx.user["theme"],
            dates=dates,
        )

    pages = [
        Page(button_name="Over Races", render=render()),
        Page(button_name="Over Time", render=render(date_list)),
    ]

    message = Message(
        ctx,
        title=f"{metric} Improvement",
        header=description,
        pages=pages,
        profile=profile,
    )

    await message.send()
