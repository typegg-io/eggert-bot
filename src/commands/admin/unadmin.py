import discord
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from database.bot.users import get_user, unadmin_user
from utils.messages import Page, Message

info = {
    "name": "unadmin",
    "aliases": [],
    "description": "Removes a user's bot admin status",
    "parameters": "<user>",
}


class Unadmin(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def unadmin(self, ctx: BotContext, user: discord.User):
        user_id = user.id
        get_user(user_id)
        unadmin_user(user_id)

        message = Message(
            ctx,
            Page(
                title="Admin Removed",
                description=f"{user.mention} is no longer a bot admin"
            )
        )

        await message.send()
