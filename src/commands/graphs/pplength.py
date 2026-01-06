from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import pplength
from utils.messages import Page, Message


log_base = 10

info = {
    "name": "pplength",
    "aliases": ["pl"],
    "description": "Returns a scatterplot of all your PP pb scores and their corresponding text length.",
    "parameters": "[username]",
    "author": 231721357484752896,
}


class PpLengthGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def pplength(self, ctx, username: str = "me"):
        username = self.get_username(ctx, username)

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        await run(ctx, profile)


async def run(ctx: commands.Context, profile: dict):
    quote_bests = get_quote_bests(profile["userId"])
    quotes = get_quotes()
    username = profile["username"]

    page = Page(
        title="pp vs. Length Comparison",
        render=lambda: pplength.render(
            username,
            quotes,
            quote_bests,
            log_base,
            ctx.user["theme"],
        )
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
