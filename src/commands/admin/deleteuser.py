import asyncio

from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin
from database.typegg.keystroke_data import delete_keystroke_data
from database.typegg.match_results import delete_match_results
from database.typegg.matches import delete_matches
from database.typegg.races import delete_races
from database.typegg.users import delete_user
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
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def deleteuser(self, ctx: commands.Context, username: str):
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


async def run(ctx: commands.Context, profile: dict):
    delete_user(profile["userId"])
    delete_races(profile["userId"])
    delete_keystroke_data(profile["userId"])
    delete_matches(profile["userId"])
    delete_match_results(profile["userId"])

    message = Message(ctx, Page(
        title="User Deleted",
        description=f"User `{profile["username"]}` has been removed from the database",
    ))

    await message.send()
