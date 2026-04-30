from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from config import GENERAL_CHANNEL_ID
from utils.messages import usable_in

info = {
    "name": "brothers",
    "aliases": [],
    "description": "Posts brothers link.",
}


class Brothers(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @usable_in(GENERAL_CHANNEL_ID)
    async def brothers(self, ctx: BotContext):
        await ctx.send("https://www.youtube.com/watch?v=2BWgmYHAxs4")
