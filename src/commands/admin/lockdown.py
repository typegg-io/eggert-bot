from discord.ext import commands

from bot_setup import is_locked, set_lockdown
from commands.base import Command
from commands.checks import is_bot_owner
from context import BotContext
from utils.messages import Message, Page

info = {
    "name": "lockdown",
    "aliases": ["ld"],
    "description": "Toggles lockdown mode, disabling all commands for non-owners.",
}


class Lockdown(Command):
    """Toggle lockdown mode, which disables commands for non-owners."""

    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def lockdown(self, ctx: BotContext):
        """Flip lockdown mode and report the new state."""
        state = not is_locked()
        set_lockdown(state)

        message = Message(ctx, Page(
            title="Lockdown Enabled" if state else "Lockdown Disabled",
            description=(
                "All commands are now disabled for regular users."
                if state else
                "Commands are available to everyone again."
            ),
        ))

        await message.send()
