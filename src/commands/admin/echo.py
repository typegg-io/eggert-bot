from discord import DMChannel
from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin

info = {
    "name": "echo",
    "aliases": ["e"],
    "description": "Echoes the given message",
    "parameters": "<message>",
}


class Echo(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def echo(self, ctx: commands.Context, *args: str):
        if not args:
            return

        if not isinstance(ctx.channel, DMChannel):
            await ctx.message.delete()

        await ctx.send(" ".join(args))
