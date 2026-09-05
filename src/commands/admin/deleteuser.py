from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_admin
from context import BotContext
from database.typegg.users import delete_user_data
from utils.colors import WARNING
from utils.errors import ProfileNotFound
from utils.messages import Message, Page
from utils.schemas import Profile

info = CommandInfo(
    name="deleteuser",
    aliases=["du"],
    description="Deletes a user from the bot's database",
    parameters="<username>",
)


class DeleteUser(Command):
    """Delete a user's data from the bot's database."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_admin()
    async def deleteuser(self, ctx: BotContext, username: str):
        """Confirm with the caller, then delete the named user."""
        try:
            profile = await self.get_profile(ctx, username)
        except ProfileNotFound:
            profile = {"userId": username, "username": username}

        message = Message(
            ctx, Page(
                title="Are You Sure?",
                description=(
                    f"You are about to permanently delete `{profile["username"]}`\n"
                    f"Please type \"confirm\" to proceed with deletion"
                ),
                color=WARNING,
            )
        )
        await message.send()

        if not await self.await_confirmation(ctx, prompt_message=message.message):
            return

        await run(ctx, profile)


async def run(ctx: BotContext, profile: Profile) -> None:
    """Delete every stored race for a user, then confirm."""
    delete_user_data(profile["userId"])

    message = Message(ctx, Page(
        title="User Deleted",
        description=f"User `{profile["username"]}` has been removed from the database",
    ))

    await message.send()
