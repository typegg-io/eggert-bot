from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from database.bot.users import migrate_command_name
from utils.messages import Page, Message

info = {
    "name": "renamecommand",
    "aliases": [],
    "description": "Migrates command usage data from an old command name to a new one.\n"
                   "Merges counts if the new name already exists for a user.",
    "parameters": "<old_name> <new_name>",
}


class RenameCommand(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def renamecommand(self, ctx: BotContext, old_name: str, new_name: str):
        await run(ctx, old_name, new_name)


async def run(ctx: BotContext, old_name: str, new_name: str):
    affected = migrate_command_name(old_name, new_name)

    message = Message(ctx, Page(
        title="Command Renamed",
        description=(
            f"Migrated `{old_name}` → `{new_name}`\n"
            f"Updated **{affected:,}** user record{'s' if affected != 1 else ''}."
        ),
    ))

    await message.send()
