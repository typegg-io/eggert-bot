from discord.ext import commands

from commands.base import Command
from utils.messages import Page, Message

info = {
    "name": "ping",
    "aliases": ["p"],
    "description": "Displays the bot's latency",
    "parameters": "",
}


class Ping(Command):
    @commands.command(aliases=info["aliases"])
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        message = Message(ctx, Page(description=f"Pong! :ping_pong: {latency}ms"))
        await message.send()
