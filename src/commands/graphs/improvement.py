from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX
from database.typegg.races import get_races
from graphs import improvement
from utils.colors import ERROR
from utils.dates import parse_date
from utils.messages import Page, Message
from utils.strings import get_argument

metrics = ["pp", "wpm"]
info = {
    "name": "improvement",
    "aliases": ["imp", "simp"],
    "description": "Displays a graph of a user's multiplayer pp or WPM over races\n"
                   "\\- `metric` defaults to pp\n"
                   f"Use `{BOT_PREFIX}simp` to view results for solo PBs",
    "parameters": "[username] [pp|wpm]",
}


class Improvement(Command):
    @commands.command(aliases=info["aliases"])
    async def improvement(self, ctx, username: Optional[str] = "me", metric: Optional[str] = None):
        solo = ctx.invoked_with == "simp"

        if metric is None:
            metric = "pp" if solo else "wpm"

        metric = get_argument(metrics, metric)
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        if solo:
            await solo_improvement(ctx, profile, metric)
        else:
            await multiplayer_improvement(ctx, profile, metric)


async def multiplayer_improvement(ctx: commands.Context, profile: dict, metric: str):
    ctx.flags.gamemode = "quickplay"
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["quoteId", metric, "timestamp", "completionType"],
        flags=ctx.flags,
    )

    if not race_list:
        message = Message(
            ctx, page=Page(
                title="No Races",
                description=f"User `{profile["username"]}` has no quickplay races",
                footer="Use -simp to view solo improvement!",
                color=ERROR,
            )
        )

        return await message.send()

    values, dates = zip(*[(race[metric], race["timestamp"]) for race in race_list])
    dnf_count = len([race for race in race_list if race["completionType"] != "finished"])
    best_average = max(np.convolve(values, np.ones(25) / 25, mode="valid"))

    if metric == "wpm":
        metric = "WPM"

    description = (
        f"**Races:** {len(values) - dnf_count:,} / "
        f"**DNFs:** {dnf_count:,}\n"
        f"**Average:** {np.mean(values):,.2f} {metric}\n"
        f"**Best:** {max(values):,.2f} {metric}\n"
    )

    if len(values) >= 25:
        description += (
            f"**Last 25 Average:** {np.mean(values[-25:]):,.2f} {metric}\n"
            f"**Best 25 Average:** {best_average:,.2f} {metric}\n"
        )

    def render(dates=None):
        return lambda: improvement.render(
            values=values,
            metric=metric,
            theme=ctx.user["theme"],
            dates=dates,
            window_size=25,
        )

    message = Message(
        ctx,
        title=f"Quickplay - {metric} Improvement",
        header=description,
        pages=[
            Page(
                button_name="Over Races",
                render=render(),
            ),
            Page(
                button_name="Over Time",
                render=render(dates)
            ),
        ],
        profile=profile,
    )

    await message.send()


async def solo_improvement(ctx: commands.Context, profile: dict, metric: str):
    ctx.flags.gamemode = "solo"
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["quoteId", metric, "timestamp"],
        flags=ctx.flags,
    )

    if not race_list:
        message = Message(
            ctx, page=Page(
                title="No Races",
                description=f"User `{profile["username"]}` has no ranked solo races",
                footer="Use -imp to view multiplayer improvement!",
                color=ERROR,
            )
        )

        return await message.send()

    pb_dict = {}
    pbs = []
    for race in race_list:
        quote_id = race["quoteId"]
        if quote_id not in pb_dict or race[metric] > pb_dict[quote_id][metric]:
            pb_dict[quote_id] = race
            pbs.append(race)
    pbs.sort(key=lambda r: parse_date(r["timestamp"]).timestamp())
    values, dates = zip(*[(race[metric], race["timestamp"]) for race in pbs])

    if metric == "wpm":
        metric = "WPM"

    description = (
        f"**PB Improvements:** {len(values):,}\n"
        f"**PB Average:** {np.mean(values):,.2f} {metric}\n"
        f"**Best:** {max(values):,.2f} {metric}\n"
    )

    def render(dates=None):
        return lambda: improvement.render(
            values=values,
            metric=metric,
            theme=ctx.user["theme"],
            dates=dates,
        )

    message = Message(
        ctx,
        title=f"Solo PBs - {metric} Improvement",
        header=description,
        pages=[
            Page(
                button_name="Over Races",
                render=render(),
            ),
            Page(
                button_name="Over Time",
                render=render(dates)
            )
        ],
        profile=profile,
    )

    await message.send()
