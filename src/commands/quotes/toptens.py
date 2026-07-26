from discord.ext import commands

from api.users import get_quote_rankings
from bot_setup import BotContext
from commands.base import Command
from utils.messages import Page, Message, Field
from utils.strings import LOADING, ordinal_number

info = {
    "name": "toptens",
    "aliases": ["10s"],
    "description": "Displays the number of quote top 10s a user appears in.",
    "parameters": "[username]",
    "examples": [
        "-10s",
        "-10s eiko",
    ],
}


class TopTens(Command):
    supported_flags = {"status"}

    @commands.command(aliases=info["aliases"])
    async def toptens(self, ctx: BotContext, username: str = None):
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: dict):
    page = Page(
        title="Top Ten Appearances",
        description=(
            f"**Quotes Typed:** {LOADING}\n"
            f"**Appearances:** {LOADING}"
        ),
        fields=[
            Field(
                title="Position Counts",
                content="\n".join(f"**{ordinal_number(i + 1)}:** {LOADING}" for i in range(10)),
                inline=True
            ),
            Field(
                title="Cumulative Counts",
                content="\n".join(f"**{ordinal_number(i + 1)}:** {LOADING}" for i in range(10)),
                inline=True
            ),
        ],
        flag_title=True,
    )
    message = Message(ctx, page=page, profile=profile)
    initial_send = message.start()

    rankings = await get_quote_rankings(
        profile["userId"],
        max_rank=10,
        status=ctx.flags.status,
    )

    quotes_typed = rankings["quotesTyped"]
    position_counts = rankings["positionCounts"]
    appearances = {i + 1: position_counts.get(str(i + 1), 0) for i in range(10)}
    total_appearances = sum(appearances.values())

    appearance_rate = f" ({total_appearances / quotes_typed:.2%})" if quotes_typed else ""
    page.description = (
        f"**Quotes Typed:** {quotes_typed:,}\n"
        f"**Appearances:** {total_appearances:,}{appearance_rate}"
    )

    page.fields = [
        Field(
            title="Position Counts",
            content="\n".join(
                f"**{ordinal_number(i + 1)}:** {appearances[i + 1]:,}"
                for i in range(10)
            ),
            inline=True
        ),
        Field(
            title="Cumulative Counts",
            content="\n".join(
                f"**{ordinal_number(i + 1)}:** {sum(appearances[k] for k in range(1, i + 2)):,}"
                for i in range(10)
            ),
            inline=True
        ),
    ]

    await initial_send
    await message.edit()
