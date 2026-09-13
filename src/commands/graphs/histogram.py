from collections.abc import Callable

import numpy as np
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.users import get_quote_bests
from graphs import histogram
from utils.messages import Field, Message, Page
from utils.schemas import Profile
from utils.strings import username_with_flag

metrics = {
    "pp": {
        "title": "pp",
        "x_label": "pp",
        "suffix": " pp",
    },
    "wpm": {
        "title": "WPM",
        "x_label": "WPM",
        "suffix": " WPM",
    },
    "accuracy": {
        "title": "Accuracy",
        "x_label": "Accuracy %",
        "suffix": "%",
    },
    "errorReactionTime": {
        "title": "Error Reaction Time",
        "x_label": "Error Reaction Time (ms)",
        "suffix": "ms"
    },
    "errorRecoveryTime": {
        "title": "Error Recovery Time",
        "x_label": "Error Recovery Time (ms)",
        "suffix": "ms"
    },
}

info = CommandInfo(
    name="histogram",
    aliases=["hg", "hist"],
    description="Displays a solo vs multiplayer histogram for a given metric.\n"
                "The react and recover metrics only include races with typos.\n",
    parameters="[username] [pp|wpm|acc|react|recover]",
    examples=[
        "-hg",
        "-hg eiko wpm",
    ],
    author=231721357484752896,
)


class Histogram(Command):
    """Graph a solo against multiplayer histogram for a metric."""

    supported_flags = {"metric", "raw", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def histogram(self, ctx: BotContext, *args: str):
        """Graph the requested metric for one user."""
        params = self.extract_params(args, metrics.keys())
        metric = params.argument or ctx.flags.metric
        self.check_raw_pp(ctx, metric == "pp")
        profile = await self.get_profile(ctx, params.username)
        await run(ctx, profile, metric)


def typo_values(values: list[float], column: str) -> list[float]:
    """Return a metric's values, keeping only races with a typo for the timing metrics."""
    if metrics[column]["suffix"] != "ms":
        return values

    return [v for v in values if v > 0]


def make_field(data: list[float], suffix: str, title: str = None, profile: Profile = None) -> Field:
    """Return the average, median, quartiles and deviation as an embed field."""
    if suffix == "ms":
        precision = 0
    else:
        precision = 2

    quartiles = np.quantile(data, [0.25, 0.75])
    return Field(
        title=title if title else username_with_flag(profile, link_user=False),
        content=(
            f"**Average:** {np.average(data):,.{precision}f}{suffix}\n"
            f"**Median:** {np.median(data):,.{precision}f}{suffix}\n"
            f"**Q1:** {quartiles[0]:,.{precision}f}{suffix}\n"
            f"**Q3:** {quartiles[1]:,.{precision}f}{suffix}\n"
            f"**Std. Dev:** ± {np.std(data):,.{precision}f}{suffix}"
        ),
        inline=True,
    )


async def run(ctx: BotContext, profile: Profile, metric: str) -> None:
    """Send a paginated histogram of one user's solo against multiplayer races."""
    user_id = profile["userId"]
    ctx.flags.gamemode = "solo"
    solo_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)
    ctx.flags.gamemode = "quickplay"
    multi_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)
    ctx.flags.gamemode = None

    def make_render(solo_values: list[float], multi_values: list[float], column: str) -> Callable:
        """Return a renderer for one metric's page."""
        return lambda: histogram.render(
            profile["username"],
            metrics[column] | {"name": column},
            solo_values,
            multi_values,
            ctx.user["theme"],
        )

    pages = []

    for column in metrics.keys():
        if ctx.flags.status != "ranked" and column == "pp":
            continue

        solo_values = typo_values([race[column] for race in solo_quote_bests if race[column] is not None], column)
        multi_values = typo_values([race[column] for race in multi_quote_bests if race[column] is not None], column)

        if column == "accuracy":
            solo_values = np.array(solo_values) * 100
            multi_values = np.array(multi_values) * 100

        metric_title = metrics[column]["title"]
        metric_suffix = metrics[column]["suffix"]
        fields = []

        if len(solo_values) > 0:
            fields.append(make_field(solo_values, metric_suffix, title="Solo"))
        if len(multi_values) > 0:
            fields.append(make_field(multi_values, metric_suffix, title="Quickplay"))

        pages.append(Page(
            title=f"{metric_title} Histogram",
            description="" if fields else "No races with a typo",
            fields=fields,
            render=make_render(solo_values, multi_values, column) if fields else None,
            button_name=metric_title,
            default=column == metric,
            flag_title=True,
        ))

    message = Message(ctx, pages=pages, profile=profile)
    await message.send()


async def run_compare(ctx: BotContext, profile1: Profile, profile2: Profile, metric: str) -> None:
    """Send a paginated histogram comparing two users across every metric."""
    quote_bests1 = get_quote_bests(profile1["userId"], columns=list(metrics.keys()), flags=ctx.flags)
    quote_bests2 = get_quote_bests(profile2["userId"], columns=list(metrics.keys()), flags=ctx.flags)

    def make_render(values1: list[float], values2: list[float], column: str) -> Callable:
        """Return a renderer for one metric's comparison page."""
        return lambda: histogram.render_compare(
            profile1["username"],
            values1,
            profile2["username"],
            values2,
            metrics[column] | {"name": column},
            ctx.user["theme"],
        )

    pages = []

    for column in metrics.keys():
        values1 = typo_values([race[column] for race in quote_bests1], column)
        values2 = typo_values([race[column] for race in quote_bests2], column)

        if column == "accuracy":
            values1 = np.array(values1) * 100
            values2 = np.array(values2) * 100

        metric_title = metrics[column]["title"]
        metric_suffix = metrics[column]["suffix"]
        fields = []

        if len(values1) > 0:
            fields.append(make_field(values1, metric_suffix, profile=profile1))
        if len(values2) > 0:
            fields.append(make_field(values2, metric_suffix, profile=profile2))

        pages.append(Page(
            title=f"{metric_title} Histogram",
            description="" if fields else "No races with a typo",
            fields=fields,
            render=make_render(values1, values2, column) if fields else None,
            button_name=metric_title,
            default=column == metric,
            flag_title=True,
        ))

    message = Message(ctx, pages=pages)
    await message.send()
