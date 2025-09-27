import asyncio

from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin
from database.typegg.races import delete_races
from database.typegg.users import delete_user
from utils.messages import Page, Message
from utils.strings import escape_formatting

info = {
    "name": "deleteuser",
    "aliases": ["du"],
    "description": "Deletes a user from the bot's database",
    "parameters": "<username>",
}


class DeleteUser(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def deleteuser(self, ctx: commands.Context, username: str):
        profile = await self.get_profile(ctx, username)

        message = Message(
            ctx, Page(
                title="Are You Sure?",
                description=f"You are about to permanently delete `{escape_formatting(profile["username"])}`"
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


async def run(ctx: commands.Context, profile: dict):
    delete_user(profile["userId"])
    delete_races(profile["userId"])

    message = Message(ctx, Page(
        title="User Deleted",
        description=f"User `{profile["username"]}` has been removed from the database",
    ))

    await message.send()
