from discord.ext import commands

from commands.base import Command
from utils.messages import usable_in

info = {
    "name": "brothers",
    "aliases": [],
    "description": "Posts brothers link",
    "parameters": "",
}


class Brothers(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(1291419824504705114)
    async def brothers(self, ctx: commands.Context):
        await ctx.send("https://www.youtube.com/watch?v=2BWgmYHAxs4")
