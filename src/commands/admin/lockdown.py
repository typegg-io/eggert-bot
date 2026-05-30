from discord.ext import commands

from bot_setup import BotContext, is_locked, set_lockdown
from commands.base import Command
from commands.checks import is_bot_owner
from utils.messages import Page, Message

info = {
    "name": "lockdown",
    "aliases": ["ld"],
    "description": "Toggles lockdown mode, disabling all commands for non-owners.",
}


class Lockdown(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def lockdown(self, ctx: BotContext):
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
