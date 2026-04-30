from discord import DMChannel
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_admin

info = {
    "name": "echo",
    "aliases": ["e"],
    "description": "Echoes the given message",
    "parameters": "<message>",
}


class Echo(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def echo(self, ctx: BotContext):
        if not ctx.raw_args:
            return

        if not isinstance(ctx.channel, DMChannel):
            await ctx.message.delete()

        await ctx.send(" ".join(ctx.raw_args))
