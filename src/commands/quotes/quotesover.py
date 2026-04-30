import numpy as np
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from utils.errors import MissingArguments
from utils.messages import Page, Message

info = {
    "name": "quotesover",
    "aliases": ["qo"],
    "description": "Displays the number of quotes a user has above a specified WPM or pp threshold.",
    "parameters": "[username] <threshold> [pp|wpm]",
    "examples": [
        "-qo eiko 200",
        "-qo eiko 1000 pp",
    ],
}


class QuotesOver(Command):
    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number"}

    @commands.command(aliases=info["aliases"])
    async def quotesover(self, ctx: BotContext, *args: str):
        if ctx.flags.number is None:
            raise MissingArguments

        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile, abs(ctx.flags.number), ctx.flags.metric)


async def run(ctx: BotContext, profile: dict, threshold: int, metric: str):
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
        title=f"Quotes Over {threshold:,} {metric}",
        description=description,
        flag_title=True,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
