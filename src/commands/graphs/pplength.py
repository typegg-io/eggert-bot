from discord import File
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import pplength
from utils.flags import Flags

info = {
    "name": "pplength",
    "aliases": ["pl"],
    "description": "Displays a scatterplot of pp PBs vs quote length.\n"
                   "Shows how performance varies across different text lengths.",
    "parameters": "[username]",
    "examples": [
        "-pl",
        "-pl eiko",
    ],
    "author": 231721357484752896,
}


class PpLengthGraph(Command):
    @commands.command(aliases=info["aliases"])
    async def pplength(self, ctx: BotContext, username: str = None):
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: dict):
    quote_bests = get_quote_bests(profile["userId"], flags=Flags(status="ranked"))
    quotes = get_quotes()

    file_name = pplength.render(
        f"pp vs. Quote Length - {profile["username"]}",
        quotes,
        quote_bests,
        ctx.user["theme"],
    )

    file = File(file_name, filename=file_name)
    await ctx.send(file=file)
