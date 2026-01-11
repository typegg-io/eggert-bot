import importlib

import discord
from discord.ext import commands

from config import DAILY_QUOTE_CHANNEL_ID
from utils.colors import ERROR
from utils.errors import UserBanned, MissingUsername, DailyQuoteChannel, MissingArguments, UnknownCommand, UnexpectedError, CommandOnCooldown, DiscordUserNotFound, MessageTooLong
from utils.logging import get_log_message, log_error
from utils.messages import check_channel_permissions


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, UserBanned):
            try:
                await send_error(ctx, error.embed)
            except discord.Forbidden:
                pass
            return

        if isinstance(error, (commands.MissingRequiredArgument, MissingArguments, MissingUsername)):
            module_path = ctx.command.callback.__module__
            command_info = importlib.import_module(module_path).info
            missing_arguments = MissingArguments().embed(
                command_info,
                show_tip=isinstance(error, MissingUsername),
            )
            return await send_error(ctx, missing_arguments)

        if isinstance(error, commands.CommandOnCooldown):
            return await send_error(ctx, CommandOnCooldown(error.retry_after).embed)

        if isinstance(error, commands.UserNotFound):
            return await send_error(ctx, DiscordUserNotFound.embed)

        if isinstance(error, discord.HTTPException):
            if error.code == 50035 and "Must be 2000 or fewer in length" in str(error):
                return await send_error(ctx, MessageTooLong.embed)

        if hasattr(error, "embed"):
            return await send_error(ctx, error.embed)

        # Ignore other channel permission failures
        if isinstance(error, commands.CheckFailure):
            if ctx.channel.id == DAILY_QUOTE_CHANNEL_ID:
                await send_error(ctx, DailyQuoteChannel.embed)
            return

        if isinstance(error, commands.CommandNotFound):
            if check_channel_permissions(ctx):
                return await send_error(ctx, UnknownCommand.embed)
            return

        await send_error(ctx, UnexpectedError(type(error).__name__).embed)

        log_message = get_log_message(ctx.message)
        log_error(log_message, error)


async def setup(bot):
    """Register the cog in the bot."""
    await bot.add_cog(ErrorHandler(bot))


async def send_error(ctx, embed):
    embed.color = embed.color or ERROR
    await ctx.send(embed=embed)
