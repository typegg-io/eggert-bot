from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_owner
from config import STATS_CHANNEL_ID

info = {
    "name": "say",
    "aliases": [],
    "description": f"Says the given message in <#{STATS_CHANNEL_ID}>",
    "parameters": "<message>",
}


class Say(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def say(self, ctx: commands.Context, *args: str):
        if not args:
            return

        message = " ".join(args)
        channel = self.bot.get_channel(STATS_CHANNEL_ID)
        if not channel:
            return

        await channel.send(message)
