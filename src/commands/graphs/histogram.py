from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import histogram
from utils.messages import Page, Message, Field
from utils.strings import get_argument

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
    "description": "Displays a solo and multiplayer histogram for a given metric.\n"
                   "The react and recover metrics exclude replays without typos.\n"
                   "\\- `metric` defaults to pp\n",
    "parameters": f"[username] [pp|wpm|acc|react|recover]",
    "author": 231721357484752896,
}


class Histogram(Command):
    @commands.command(aliases=info["aliases"])
    async def histogram(self, ctx, username: Optional[str] = "me", metric: Optional[str] = "pp"):
        metric = get_argument(metrics.keys(), metric)
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str):
    user_id = profile["userId"]
    solo_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), gamemode="solo")
    multi_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), gamemode="quickplay")

    def make_field(title: str, data: list[float], suffix: str):
        if suffix == "ms":
            data = [v for v in data if v > 0]
            precision = 0
        else: 
            precision = 2

        quartiles = np.quantile(data, [0.25, 0.75])

        content = (
            f"**Average:** {np.average(data):,.{precision}f}{suffix}\n"
            f"**Median:** {np.median(data):,.{precision}f}{suffix}\n"
            f"**Q1:** {quartiles[0]:,.{precision}f}{suffix}\n"
            f"**Q3:** {quartiles[1]:,.{precision}f}{suffix}\n"
            f"**Std. Dev:** ± {np.std(data):,.{precision}f}{suffix}"
        )

        return Field(title=title, content=content, inline=True)

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
            fields.append(make_field("Solo", solo_values, suffix=metric_suffix))
        if len(multi_values) > 0:
            fields.append(make_field("Quickplay", multi_values, suffix=metric_suffix))

        pages.append(Page(
            title=f"{metric_title} Histogram",
            fields=fields,
            render=make_render(solo_values, multi_values, column),
            button_name=metric_title,
            default=column == metric,
        ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
