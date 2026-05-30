import subprocess

from discord import Embed
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from config import STAGING
from utils.messages import Page, Message

info = {
    "name": "restart",
    "aliases": [],
    "description": "Restarts the bot process.",
}


class Restart(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def restart(self, ctx: BotContext):
        if STAGING:
            return

        message = Message(ctx, Page(title="Restarting..."))
        await message.send()

        subprocess.Popen(
            ["sudo", "systemctl", "restart", "eggert-bot"],
            start_new_session=True,
        )
