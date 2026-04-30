from typing import List

import numpy as np
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import top as top_graph
from utils.errors import NoRankedRaces
from utils.messages import Page, Message

max_users = 5

info = {
    "name": "top",
    "aliases": ["50", "100", "250", "500", "1000"],
    "description": "Displays a user's top n quote PBs ordered by pp.\n"
                   "Use `n` to set how many quotes to show (default 50).\n"
                   f"Supports up to {max_users} users.",
    "parameters": f"[username1] ... [username{max_users}] [n]",
    "examples": [
        "-top",
        "-top eiko",
        "-top eiko me",
        "-top eiko me 1000",
    ],
    "author": 231721357484752896,
}


class Top(Command):
    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number"}

    @commands.command(aliases=info["aliases"])
    async def top(self, ctx: BotContext, *args: str):
        if ctx.invoked_with.isnumeric():
            n = int(ctx.invoked_with)
        else:
            n = int(abs(ctx.flags.number)) if ctx.flags.number is not None else 250
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles, n, ctx.flags.metric)


def get_optimization_level(pp_values):
    """Returns an optimization level for a list of values based on curvature."""
    anchor_percentile = 98  # Ignoring "farm" outliers
    pp = np.array(pp_values, dtype=float)
    pp_anchor = np.percentile(pp, anchor_percentile)

    deviation = np.mean(np.abs(pp - pp_anchor))
    return 1 - deviation / pp_anchor


async def run(ctx: BotContext, profiles: List[dict], n: int, metric: str):
    top_scores = []
    username = profiles[0]["username"]
    quote_list = get_quotes()

    rows = []
    for profile in profiles:
        quote_bests = get_quote_bests(
            profile["userId"],
            columns=[metric, "quoteId"],
            order_by=metric,
            limit=n,
            flags=ctx.flags,
        )
        values = [race[metric] for race in quote_bests]
        quote_ids = [race["quoteId"] for race in quote_bests]
        difficulties = [quote_list[quote_id]["difficulty"] for quote_id in quote_ids]
        total = sum(v * (0.97 ** i) for i, v in enumerate(values))

        if not values:
            raise NoRankedRaces(username)

        top_scores.append({
            "username": profile["username"],
            "values": values,
            "difficulties": difficulties,
            "total": total,
        })

        if profile["userId"] == ctx.user["userId"]:
            username = profile["username"]

        row = {
            "username": profile["username"],
            "max": max(values),
            "avg": np.mean(values),
            "min": min(values),
            "total": total,
        }

        if metric == "pp":
            row["opt"] = get_optimization_level(values[:250])

        rows.append(row)

    top_scores.sort(key=lambda x: -x["total"])
    rows.sort(key=lambda x: -x["total"])

    decimals = 2 if metric == "wpm" else 0
    dec_format = f",.{decimals}f"

    username_width = max(len("Username"), max(len(row["username"]) for row in rows))
    username_width = min(username_width, 10)
    max_width = max(len("Max"), max(len(f"{row['max']:{dec_format}}") for row in rows))
    avg_width = max(len("Average"), max(len(f"{row['avg']:{dec_format}}") for row in rows))
    min_width = max(len("Min"), max(len(f"{row['min']:{dec_format}}") for row in rows))

    description = "```\n"

    if metric == "pp":
        total_width = max(len("Total"), max(len(f"{row['total']:,.0f}") for row in rows))
        opt_width = 9

        description += f"{"Username":<{username_width}} {"Total":<{total_width}} {"Max":<{max_width}} {"Average":<{avg_width}} {"Min":<{min_width}} {"Optimized":<{opt_width}}\n"
        description += f"{"-" * username_width} {"-" * total_width} {"-" * max_width} {"-" * avg_width} {"-" * min_width} {"-" * opt_width}\n"

        for row in rows:
            if len(row["username"]) > 9:
                row["username"] = row["username"][:9] + "…"
            description += f"{row["username"]:<{username_width}} "
            description += f"{row["total"]:<{total_width},.0f} "
            description += f"{row["max"]:<{max_width}{dec_format}} "
            description += f"{row["avg"]:<{avg_width}{dec_format}} "
            description += f"{row["min"]:<{min_width}{dec_format}} "
            description += f"{row["opt"]:<{opt_width}.2%}\n"
    else:
        description += f"{"Username":<{username_width}} {"Max":<{max_width}} {"Average":<{avg_width}} {"Min":<{min_width}}\n"
        description += f"{"-" * username_width} {"-" * max_width} {"-" * avg_width} {"-" * min_width}\n"

        for row in rows:
            if len(row["username"]) > 9:
                row["username"] = row["username"][:9] + "…"
            description += f"{row["username"]:<{username_width}} "
            description += f"{row["max"]:<{max_width}{dec_format}} "
            description += f"{row["avg"]:<{avg_width}{dec_format}} "
            description += f"{row["min"]:<{min_width}{dec_format}}\n"

    description += "```"

    if metric == "wpm":
        metric = "WPM"

    page = Page(
        title=f"Top {n:,} {metric} Quotes",
        description=description,
        render=lambda: top_graph.render(
            username,
            top_scores,
            n,
            metric,
            ctx.user["theme"],
        ),
        flag_title=True,
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()
