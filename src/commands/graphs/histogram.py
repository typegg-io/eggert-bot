from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import histogram
from utils.errors import SameUsername, MissingArguments
from utils.messages import Page, Message, Field
from utils.strings import get_argument, username_with_flag

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
    "aliases": ["hg", "hist", "histcompare", "hc"],
    "description": "Displays a solo and multiplayer histogram for a given metric.\n"
                   "Use `histcompare` to compare two users.\n"
                   "The react and recover metrics exclude replays without typos.\n"
                   "\\- `metric` defaults to pp\n",
    "parameters": "[username] [username2] [pp|wpm|acc|react|recover]",
    "author": 231721357484752896,
}


class Histogram(Command):
    @commands.command(aliases=info["aliases"])
    async def histogram(self, ctx, username: Optional[str] = "me", *args):
        if ctx.invoked_with in ["histcompare", "hc"]:
            if not args:
                raise MissingArguments
            username2 = args[0]
            metric = "pp" if len(args) < 2 else args[1]
            metric = get_argument(metrics.keys(), metric)
            username, username2 = self.get_usernames(ctx, username, username2)
            profile1 = await self.get_profile(ctx, username, races_required=True)
            profile2 = await self.get_profile(ctx, username2, races_required=True)
            if profile1["username"] == profile2["username"]:
                raise SameUsername
            await self.import_user(ctx, profile1)
            await self.import_user(ctx, profile2)
            await run_compare(ctx, profile1, profile2, metric)
        else:
            metric = get_argument(metrics.keys(), args[0] if args else "pp")
            profile = await self.get_profile(ctx, username, races_required=True)
            await self.import_user(ctx, profile)
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


async def run(ctx: commands.Context, profile: dict, metric: str):
    user_id = profile["userId"]
    ctx.flags.status = ctx.flags.status or "ranked"
    ctx.flags.gamemode = "solo"
    solo_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)
    ctx.flags.gamemode = "quickplay"
    multi_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), flags=ctx.flags)

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
        solo_values = [race[column] for race in solo_quote_bests]
        multi_values = [race[column] for race in multi_quote_bests]

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
        ))

    message = Message(ctx, pages=pages, profile=profile)
    await message.send()


async def run_compare(ctx: commands.Context, profile1: dict, profile2: dict, metric: str):
    ctx.flags.status = ctx.flags.status or "ranked"
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
        ))

    message = Message(ctx, pages=pages)
    await message.send()
