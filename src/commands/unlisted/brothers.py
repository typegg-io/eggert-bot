from discord.ext import commands
from commands.base import Command

info = {
    "name": "brothers",
    "aliases": [],
    "description": "Posts brothers link",
    "parameters": "",
}

class Brothers(Command):
    @commands.command(aliases=info["aliases"])
    async def brothers(self, ctx: commands.Context, arg: None = None):
        await ctx.send("https://www.youtube.com/watch?v=2BWgmYHAxs4")