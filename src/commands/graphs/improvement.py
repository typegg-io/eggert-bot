import numpy as np
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from graphs import improvement
from utils.colors import ERROR
from utils.dates import parse_date
from utils.messages import Page, Message, Field

metrics = ["pp", "wpm"]
info = {
    "name": "improvement",
    "aliases": ["imp", "simp"],
    "description": "Displays a user's pp or WPM improvement over races.\n"
                   "Use `-simp` to view solo PBs instead of multiplayer.\n",
    "parameters": "[username] [pp|wpm]",
    "examples": [
        "-imp",
        "-imp eiko wpm",
        "-simp eiko",
    ],
}


class Improvement(Command):
    supported_flags = {"metric", "raw", "status", "language"}

    @commands.command(aliases=info["aliases"])
    async def improvement(self, ctx: BotContext, *args: str):
        solo = ctx.invoked_with == "simp"
        metric = "pp" if solo else "wpm"

        if ctx.explicit_flags.get("metric"):  # Overriding default metric
            metric = ctx.explicit_flags["metric"].lstrip("-")

        if ctx.flags.status != "ranked":  # Unranked quotes are 0 pp
            metric = "wpm"

        username = args[0] if args else None
        profile = await self.get_profile(ctx, username)

        if solo:
            await solo_improvement(ctx, profile, metric)
        else:
            await multiplayer_improvement(ctx, profile, metric)


def get_window_size(n: int, min_n: int = 25, max_n: int = 500):
    window_size = int(min(max_n, max(min_n, np.sqrt(n) * 5)))
    return window_size if window_size < n else 1


async def multiplayer_improvement(ctx: BotContext, profile: dict, metric: str):
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

    quote_list = get_quotes()

    values, dates, difficulties = zip(*[
        (race[metric], race["timestamp"], quote_list[race["quoteId"]]["difficulty"])
        for race in race_list
        if race["completionType"] == "finished"
    ])

    moving_25 = np.convolve(values, np.ones(25) / 25, mode="valid")
    best_25 = max(moving_25)
    last_25 = moving_25[-1]

    moving_100 = np.convolve(values, np.ones(100) / 100, mode="valid")
    best_100 = max(moving_100)
    last_100 = moving_100[-1]

    window = get_window_size(len(values))
    moving_average = np.convolve(values, np.ones(window) / window, mode="valid")
    best_average = max(moving_average)
    last_average = moving_average[-1]

    finishes_covered = window
    quits_in_average = 0

    for race in reversed(race_list):
        if race["completionType"] == "finished":
            finishes_covered -= 1
            if finishes_covered == 0:
                break
        else:
            quits_in_average += 1

    dnf_indices = []
    dnf = False

    for race in race_list:
        if race["completionType"] == "finished":
            dnf_indices.append(dnf)
            dnf = False
        else:
            dnf = True

    if metric == "wpm":
        metric = "WPM"

    description = f"**Races:** {len(values):,}\n"

    fields = []

    if window > 25:
        fields.append(Field(
            title="Average of 25",
            content=f"– Recent: {last_25:,.2f} WPM | Best: {best_25:,.2f} WPM",
        ))

    if window > 100:
        fields.append(Field(
            title="Average of 100",
            content=f"– Recent: {last_100:,.2f} WPM | Best: {best_100:,.2f} WPM",
        ))

    fields.append(Field(
        title=f"Average of {window}",
        content=(
            f"– Recent: {last_average:,.2f} WPM | Best: {best_average:,.2f} WPM\n"
            f"– Completion: {window / (window + quits_in_average):.2%}"
        ),
    ))

    message = Message(
        ctx,
        title=f"{metric} Improvement",
        header=description,
        pages=[
            Page(
                fields=fields,
                button_name="Over Races",
                render=lambda: improvement.render_over_races(
                    values=values,
                    difficulties=difficulties,
                    metric=metric,
                    theme=ctx.user["theme"],
                    window_size=window,
                    dnf_indices=dnf_indices,
                ),
                flag_title=True,
            ),
            Page(
                fields=fields,
                button_name="Over Time",
                render=lambda: improvement.render_over_time(
                    values=values,
                    metric=metric,
                    theme=ctx.user["theme"],
                    dates=dates,
                    window_size=window,
                    dnf_indices=dnf_indices,
                ),
                flag_title=True,
            ),
        ],
        profile=profile,
    )

    await message.send()


async def solo_improvement(ctx: BotContext, profile: dict, metric: str):
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

    quote_list = get_quotes()
    values, dates, quote_ids = zip(*[(race[metric], race["timestamp"], race["quoteId"]) for race in pbs])
    difficulties = [quote_list[qid]["difficulty"] for qid in quote_ids]

    window = get_window_size(len(values))

    if metric == "wpm":
        metric = "WPM"

    description = (
        f"**PB Improvements:** {len(values):,}\n"
        f"**PB Average:** {np.mean(values):,.2f} {metric}\n"
        f"**Best:** {max(values):,.2f} {metric}\n"
    )

    message = Message(
        ctx,
        title=f"{metric} PB Improvement",
        header=description,
        pages=[
            Page(
                button_name="Over Races",
                render=lambda: improvement.render_over_races(
                    values=values,
                    difficulties=difficulties,
                    metric=metric,
                    theme=ctx.user["theme"],
                    window_size=window,
                ),
                flag_title=True,
            ),
            Page(
                button_name="Over Time",
                render=lambda: improvement.render_over_time(
                    values=values,
                    metric=metric,
                    theme=ctx.user["theme"],
                    dates=dates,
                    window_size=window,
                ),
                flag_title=True,
            )
        ],
        profile=profile,
    )

    await message.send()
