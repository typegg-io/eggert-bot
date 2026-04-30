import numpy as np
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import histogram
from utils.messages import Page, Message, Field
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

info = {
    "name": "histogram",
    "aliases": ["hg", "hist"],
    "description": "Displays a solo vs multiplayer histogram for a given metric.\n"
                   "The react and recover metrics only include races with typos.\n",
    "parameters": "[username] [pp|wpm|acc|react|recover]",
    "examples": [
        "-hg",
        "-hg eiko wpm",
    ],
    "author": 231721357484752896,
}


class Histogram(Command):
    supported_flags = {"metric", "raw", "status", "language"}

    @commands.command(aliases=info["aliases"])
    async def histogram(self, ctx: BotContext, *args: str):
        params = self.extract_params(args, metrics.keys())
        metric = params.argument or ctx.flags.metric
        profile = await self.get_profile(ctx, params.username)
        await run(ctx, profile, metric)


def make_field(data: list[float], suffix: str, title: str = None, profile: dict = None):
    if suffix == "ms":
        data = [v for v in data if v > 0]
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


async def run(ctx: BotContext, profile: dict, metric: str):
    user_id = profile["userId"]
    ctx.flags.gamemode = "solo"
    solo_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)
    ctx.flags.gamemode = "quickplay"
    multi_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)
    ctx.flags.gamemode = None

    def make_render(solo_values: list[float], multi_values: list[float], column: str):
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

        solo_values = [race[column] for race in solo_quote_bests if race[column] is not None]
        multi_values = [race[column] for race in multi_quote_bests if race[column] is not None]

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
            fields=fields,
            render=make_render(solo_values, multi_values, column),
            button_name=metric_title,
            default=column == metric,
            flag_title=True,
        ))

    message = Message(ctx, pages=pages, profile=profile)
    await message.send()


async def run_compare(ctx: BotContext, profile1: dict, profile2: dict, metric: str):
    quote_bests1 = get_quote_bests(profile1["userId"], columns=list(metrics.keys()), flags=ctx.flags)
    quote_bests2 = get_quote_bests(profile2["userId"], columns=list(metrics.keys()), flags=ctx.flags)

    def make_render(values1: list[float], values2: list[float], column: str):
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
        values1 = [race[column] for race in quote_bests1]
        values2 = [race[column] for race in quote_bests2]

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
            fields=fields,
            render=make_render(values1, values2, column),
            button_name=metric_title,
            default=column == metric,
            flag_title=True,
        ))

    message = Message(ctx, pages=pages)
    await message.send()
