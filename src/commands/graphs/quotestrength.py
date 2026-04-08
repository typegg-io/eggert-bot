from typing import List

import numpy as np
from discord.ext import commands

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
                   f"Based on top 250 ranked quotes.\n"
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
    async def quotestrength(self, ctx, *other_users: str):
        usernames = list(dict.fromkeys(other_users))[:max_users] or [ctx.user["userId"]]
        profiles = []

        for username in usernames:
            profile = await self.get_profile(ctx, username, races_required=True)
            profiles.append(profile)
            await self.import_user(ctx, profile)

        await run(ctx, profiles)


async def run(ctx: commands.Context, profiles: List[dict]):
    quote_list = get_quotes()

    ranked_quotes = [q for q in quote_list.values() if q.get("ranked")]
    lengths = np.array([len(q["text"]) for q in ranked_quotes])
    log_lengths = np.log(lengths)
    complexities = np.array([q["complexity"] for q in ranked_quotes])
    sorted_complexities = np.sort(complexities)

    len_p10 = np.percentile(log_lengths, 10)
    len_p90 = np.percentile(log_lengths, 90)

    users = []

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
        x = np.clip((weighted_log_length - len_p10) / (len_p90 - len_p10) * 2 - 1, -1, 1)

        # Percentile -> [-1, 1]
        p = np.searchsorted(sorted_complexities, weighted_complexity, side="right") / len(sorted_complexities)
        y = np.clip(p * 2 - 1, -1, 1)

        users.append({
            "username": profile["username"],
            "x": x,
            "y": y,
        })

    page = Page(
        title="Quote Strength Compass",
        render=lambda: qs_graph.render(users, ctx.user["theme"]),
    )

    message = Message(ctx, page=page)
    await message.send()
