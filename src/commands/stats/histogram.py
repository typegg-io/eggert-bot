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
    },
    "wpm": {
        "title": "WPM",
        "x_label": "WPM",
    },
    "accuracy": {
        "title": "Accuracy",
        "x_label": "Accuracy %",
    },
    "errorReactionTime": {
        "title": "Error Reaction Time",
        "x_label": "Error Reaction Time (ms)",
    },
    "errorRecoveryTime": {
        "title": "Error Recovery Time",
        "x_label": "Error Recovery Time (ms)",
    },
}

info = {
    "name": "histogram",
    "aliases": ["hg", "hist"],
    "description": "Displays a solo and multiplayer histogram for a given metric.\n"
                   "\\- `metric` defaults to pp\n",
    "parameters": f"<username> [pp|wpm|acc|react|recover]",
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
    multi_quote_bests = get_quote_bests(user_id, columns=metrics.keys(), gamemode="multiplayer")

    solo_values = [race[metric] for race in solo_quote_bests]
    multi_values = [race[metric] for race in multi_quote_bests]

    if metric == "accuracy":
        solo_values = np.array(solo_values) * 100
        multi_values = np.array(multi_values) * 100

    def make_field(title: str, data: list[float]):
        quartiles = np.quantile(data, [0.25, 0.75])
        content = (
            f"**Average:** {np.average(data):,.2f}\n"
            f"**Median:** {np.median(data):,.2f}\n"
            f"**Q1:** {quartiles[0]:,.2f} | **Q3:** {quartiles[1]:,.2f}\n"
            f"**Std. Deviation:** ± {np.std(data):,.2f}"
        )

        return Field(title=title, content=content, inline=True)

    fields = [
        make_field("Solo", solo_values),
        make_field("Multiplayer", multi_values),
    ]

    page = Page(
        title=f"{metrics[metric]["title"]} Histogram",
        fields=fields,
        render=lambda: histogram.render(
            profile["username"],
            metrics[metric] | {"name": metric},
            solo_values,
            multi_values,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
