import discord
from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin
from database.bot.users import get_user, ban_user
from utils.messages import Page, Message

info = {
    "name": "ban",
    "aliases": [],
    "description": "Bans a user from using bot commands",
    "parameters": "<user>",
}


class Ban(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def ban(self, ctx: commands.Context, user: discord.User):
        user_id = user.id
        get_user(user_id)

        if user_id == ctx.author.id:
            message = Message(
                ctx, Page(
                    title="Prevented Self-Ban",
                    description="Why would you want to do that? :frowning:"
                )
            )
        else:
            ban_user(user_id)
            message = Message(
                ctx,
                Page(
                    title="User Banned",
                    description=f"{user.mention} has been banned from using bot commands"
                )
            )

        await message.send()
