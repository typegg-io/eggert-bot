import subprocess

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_owner
from config import STAGING
from context import BotContext
from utils.messages import Message, Page

info = CommandInfo(
    name="restart",
    aliases=[],
    description="Restarts the bot process.",
)


class Restart(Command):
    """Restart the bot process."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_owner()
    async def restart(self, ctx: BotContext):
        """Restart the systemd unit, doing nothing on staging."""
        if STAGING:
            return

        message = Message(ctx, Page(title="Restarting..."))
        await message.send()

        subprocess.Popen(
            ["sudo", "systemctl", "restart", "eggert-bot"],
            start_new_session=True,
        )
