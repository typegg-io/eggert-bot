from discord import File
from discord.ext import commands

from commands.base import Command
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.users import get_quote_bests
from graphs import pplength
from utils.flags import Flags
from utils.schemas import Profile

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
    """Graph a scatterplot of pp personal bests against quote length."""

    @commands.command(aliases=info["aliases"])
    async def pplength(self, ctx: BotContext, username: str = None):
        """Graph one user's pp against quote length."""
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a scatterplot of the user's ranked quote bests by length."""
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
