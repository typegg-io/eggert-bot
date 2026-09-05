from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_owner
from config import STATS_CHANNEL_ID
from context import BotContext

info = CommandInfo(
    name="say",
    aliases=[],
    description=f"Says the given message in <#{STATS_CHANNEL_ID}>",
    parameters="<message>",
)


class Say(Command):
    """Post a message to the stats channel as the bot."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_owner()
    async def say(self, ctx: BotContext):
        """Send the arguments to the stats channel."""
        if not ctx.raw_args:
            return

        message = " ".join(ctx.raw_args)
        channel = self.bot.get_channel(STATS_CHANNEL_ID)
        if not channel:
            return

        await channel.send(message)
