import asyncio

from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_admin
from database.typegg.users import delete_user_data
from utils.colors import WARNING
from utils.errors import ProfileNotFound
from utils.messages import Page, Message

info = {
    "name": "deleteuser",
    "aliases": ["du"],
    "description": "Deletes a user from the bot's database",
    "parameters": "<username>",
}


class DeleteUser(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def deleteuser(self, ctx: BotContext, username: str):
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

        def check(message):
            return message.author == ctx.author and message.content.lower() == "confirm"

        try:
            await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            return
        else:
            await run(ctx, profile)


async def run(ctx: BotContext, profile: dict):
    delete_user_data(profile["userId"])

    message = Message(ctx, Page(
        title="User Deleted",
        description=f"User `{profile["username"]}` has been removed from the database",
    ))

    await message.send()
