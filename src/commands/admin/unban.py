import discord
from discord.ext import commands

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
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def unban(self, ctx: commands.Context, user: discord.User):
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
