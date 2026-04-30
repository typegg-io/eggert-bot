from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from utils.messages import Page, Message

info = {
    "name": "ping",
    "aliases": ["p"],
    "description": "Displays the bot's latency.",
    "examples": [
        "-ping",
    ],
}


class Ping(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    async def ping(self, ctx: BotContext):
        latency = round(self.bot.latency * 1000)
        message = Message(ctx, Page(description=f"Pong! :ping_pong: {latency}ms"))
        await message.send()
