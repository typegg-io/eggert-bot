import discord
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from database.bot.users import get_user, admin_user
from utils.messages import Page, Message

info = {
    "name": "admin",
    "aliases": [],
    "description": "Adds a user as a bot admin",
    "parameters": "<user>",
}


class Admin(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def admin(self, ctx: BotContext, user: discord.User):
        user_id = user.id
        get_user(user_id)
        admin_user(user_id)

        message = Message(
            ctx,
            Page(
                title="Admin Added",
                description=f"{user.mention} has been added as a bot admin"
            )
        )

        await message.send()
