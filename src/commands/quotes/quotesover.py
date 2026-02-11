from typing import Optional

import numpy as np
from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from utils.messages import Page, Message
from utils.strings import get_argument, parse_number, get_flag_title

info = {
    "name": "quotesover",
    "aliases": ["qo"],
    "description": "Displays the number of quotes a user has above a specified threshold",
    "parameters": "<username> <threshold> [pp|wpm]",
}


class QuotesOver(Command):
    @commands.command(aliases=info["aliases"])
    async def quotesover(
        self, ctx, username: str, threshold: str, metric: Optional[str] = "wpm"):
        threshold = parse_number(threshold)
        metric = get_argument(["pp", "wpm"], metric)

        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        await run(ctx, profile, threshold, metric)


async def run(ctx: commands.Context, profile: dict, threshold: int, metric: str):
    ctx.flags.status = ctx.flags.status or "ranked"
    quote_bests = get_quote_bests(
        profile["userId"],
        columns=["quoteId", metric],
        order_by=metric,
        flags=ctx.flags,
    )

    quote_list = get_quotes()

    values = []
    difficulties = []

    for quote in quote_bests:
        if quote[metric] < threshold:
            break

        values.append(quote[metric])
        difficulties.append(quote_list[quote["quoteId"]]["difficulty"])

    over_count = len(values)
    avg_value = np.mean(values)
    best_value = max(values) if over_count > 0 else 0
    avg_difficulty = np.mean(difficulties) if over_count > 0 else 0

    if metric == "wpm":
        metric = "WPM"

    description = f"**Quotes Over:** {over_count:,} of {len(quote_bests):,}\n"

    if over_count > 0:
        description += (
            f"**Best:** {best_value:,.2f} {metric}\n"
            f"**Average:** {avg_value:,.2f} {metric}\n"
        )

    if over_count > 0:
        description += f"**Average Difficulty:** {avg_difficulty:.2f}★\n"

    page = Page(
        title=f"Quotes Over {threshold:,} {metric}" + get_flag_title(ctx.flags),
        description=description,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
