from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.performance.best import run
from utils.errors import NotSubscribed

info = {
    "name": "worst",
    "aliases": ["bottom"],
    "description": "Displays a user's bottom 100 quotes\n"
                   "\\- `metric` defaults to pp",
    "parameters": "[username] [pp|wpm]",
}


class Worst(Command):
    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number_range"}

    @commands.command(aliases=info["aliases"])
    async def worst(self, ctx: BotContext, username: str = None):
        if ctx.flags.metric == "pp" and ctx.flags.raw and not ctx.user["isGgPlus"]:
            raise NotSubscribed("raw pp stats")

        profile = await self.get_profile(ctx, username)
        await run(ctx, profile, ctx.flags.metric, reverse=False)
