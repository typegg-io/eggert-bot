from typing import Optional

from discord.ext import commands

from api.users import get_quotes
from commands.base import Command
from utils.messages import Page, Message, Field
from utils.strings import LOADING, ordinal_number

info = {
    "name": "toptens",
    "aliases": ["10s"],
    "description": "Displays the number of quote top 10s a user appears in",
    "parameters": "[username]",
}


class TopTens(Command):
    @commands.command(aliases=info["aliases"])
    async def toptens(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username, races_required=True)
        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
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
        ]
    )
    message = Message(ctx, page=page, profile=profile)
    initial_send = message.start()

    first_page = await get_quotes(profile["username"], per_page=1000)
    total_pages = first_page["totalPages"]
    quotes = first_page["quotes"]
    for i in range(2, total_pages + 1):
        results = await get_quotes(profile["username"], per_page=1000, page=i)
        quotes += results["quotes"]

    appearances = {i + 1: 0 for i in range(11)}
    for quote in quotes:
        global_rank = quote["globalRank"]
        if global_rank <= 10:
            appearances[global_rank] += 1

    quotes_typed = len(quotes)
    total_appearances = sum(appearances.values())
    page.description = (
        f"**Quotes Typed:** {quotes_typed:,}\n"
        f"**Appearances:** {total_appearances:,} ({total_appearances / quotes_typed:.2%})"
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
