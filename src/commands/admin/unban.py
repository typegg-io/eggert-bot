import discord
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_admin
from context import BotContext
from database.bot.users import unban_user
from utils.messages import Message, Page

info = CommandInfo(
    name="unban",
    aliases=[],
    description="Unbans a user from using bot commands",
    parameters="<user>",
)


class Unban(Command):
    """Unban a user from using bot commands."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_admin()
    async def unban(self, ctx: BotContext, user: discord.User):
        """Lift the named user's ban."""
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
