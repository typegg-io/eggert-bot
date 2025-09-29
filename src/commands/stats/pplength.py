from discord.ext import commands

from api.users import get_quotes
from commands.base import Command
from database.typegg.users import get_quote_bests
from graphs import pplength
from utils.messages import Page, Message


info = {
    "name": "pplength",
    "aliases": ["pl"],
    "description": "Returns a scatterplot of all your PP pb scores and their corresponding text length.",
    "parameters": "<username>",
}


class PpLengthGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def ppLength(self, ctx, username: str = "me"):
        username = self.get_username(ctx, username)

        profile = await self.get_profile(ctx, username)
        await self.import_user(ctx, profile)

        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    quote_bests = get_quote_bests(profile["userId"])
    quotes = []
    pages = 1
    page = 1

    while 1 <= page < 100 and pages <= pages:
        data = await get_quotes(profile["userId"], per_page=1000, page=page)
        new_quotes = data["quotes"]

        if new_quotes is None:
            break

        quotes += new_quotes
        pages = data["totalPages"]
        page += 1

    username = profile["username"]

    page = Page(
        title="pp vs. Length Comparison",
        render=lambda: pplength.render(
            username,
            quotes,
            quote_bests,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()

