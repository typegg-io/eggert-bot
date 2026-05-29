from typing import List

import numpy as np
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import quotestrength as qs_graph
from utils.errors import NoRankedRaces
from utils.messages import Page, Message

max_users = 5

info = {
    "name": "quotestrength",
    "aliases": ["qs"],
    "description": "Displays a compass showing where a user's pp comes from.\n"
                   "Axes are short/long (character count) and simple/complex (complexity).\n"
                   "For a single user, a heatmap is shown behind the dot representing play density.\n"
                   "The dot is where pp comes from, the heatmap shows what is played the most.\n"
                   "Based on top 250 ranked quotes.\n"
                   f"Supports up to {max_users} users.",
    "parameters": f"[username1] ... [username{max_users}]",
    "examples": [
        "-quotestrength",
        "-quotestrength eiko",
        "-quotestrength eiko me",
    ],
}


class QuoteStrength(Command):
    @commands.command(aliases=info["aliases"])
    async def quotestrength(self, ctx: BotContext, *args: str):
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles)


def _quote_xy(quote, len_p10, len_p90, sorted_complexities):
    log_len = np.log(len(quote["text"]))
    raw = (log_len - len_p10) / (len_p90 - len_p10) * 2 - 1
    x = float(np.tanh(raw * 1.2))
    p = np.searchsorted(sorted_complexities, quote["complexity"], side="right") / len(sorted_complexities)
    y = float(np.clip(p * 2 - 1, -1, 1))
    return x, y


async def run(ctx: BotContext, profiles: List[dict]):
    quote_list = get_quotes()

    ranked_quotes = [q for q in quote_list.values() if q.get("ranked")]
    lengths = np.array([len(q["text"]) for q in ranked_quotes])
    log_lengths = np.log(lengths)
    complexities = np.array([q["complexity"] for q in ranked_quotes])
    sorted_complexities = np.sort(complexities)

    len_p10 = np.percentile(log_lengths, 10)
    len_p90 = np.percentile(log_lengths, 90)

    users = []
    quote_bests = None

    for profile in profiles:
        quote_bests = get_quote_bests(
            profile["userId"],
            columns=["pp", "quoteId"],
            order_by="pp",
            limit=250,
        )

        if not quote_bests:
            raise NoRankedRaces(profile["username"])

        weights = np.array([0.97 ** i for i in range(len(quote_bests))])
        total_weight = np.sum(weights)

        values = np.array([
            np.log(len(quote_list[r["quoteId"]]["text"]))
            for r in quote_bests
        ])
        weights_arr = weights / total_weight

        # sort by value
        sorted_idx = np.argsort(values)
        values = values[sorted_idx]
        weights_arr = weights_arr[sorted_idx]

        cum_weights = np.cumsum(weights_arr)
        weighted_log_length = values[np.searchsorted(cum_weights, 0.5)]

        weighted_complexity = sum(
            quote_list[r["quoteId"]]["complexity"] * w
            for r, w in zip(quote_bests, weights)
        ) / total_weight

        # Normalization
        raw = (weighted_log_length - len_p10) / (len_p90 - len_p10)
        raw = raw * 2 - 1
        x = np.tanh(raw * 1.2)

        # Percentile -> [-1, 1]
        p = np.searchsorted(sorted_complexities, weighted_complexity, side="right") / len(sorted_complexities)
        y = np.clip(p * 2 - 1, -1, 1)

        users.append({
            "username": profile["username"],
            "x": x,
            "y": y,
        })

    heatmap_points = None
    if len(profiles) == 1:
        heatmap_points = [
            _quote_xy(quote_list[r["quoteId"]], len_p10, len_p90, sorted_complexities)
            for r in quote_bests
            if r["quoteId"] in quote_list
        ]

    page = Page(
        title="Quote Strength Compass",
        render=lambda: qs_graph.render(users, ctx.user["theme"], heatmap_points),
    )

    message = Message(ctx, page=page)
    await message.send()
