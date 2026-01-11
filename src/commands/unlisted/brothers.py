from discord.ext import commands

from commands.base import Command
from config import GENERAL_CHANNEL_ID
from utils.messages import usable_in

info = {
    "name": "brothers",
    "aliases": [],
    "description": "Posts brothers link",
    "parameters": "",
}


class Brothers(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(GENERAL_CHANNEL_ID)
    async def brothers(self, ctx: commands.Context):
        await ctx.send("https://www.youtube.com/watch?v=2BWgmYHAxs4")
