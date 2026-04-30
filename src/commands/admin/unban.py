import discord
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_admin
from database.bot.users import unban_user
from utils.messages import Page, Message

info = {
    "name": "unban",
    "aliases": [],
    "description": "Unbans a user from using bot commands",
    "parameters": "<user>",
}


class Unban(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def unban(self, ctx: BotContext, user: discord.User):
        user_id = user.id
        unban_user(user_id)

        message = Message(
            ctx,
            Page(
                title="User Banned",
                description=f"{user.mention} has been unbanned"
            )
        )
        await message.send()
