import importlib

import discord
from discord.ext import commands

from utils.colors import ERROR
from utils.errors import UserBanned, MissingUsername, DailyQuoteChannel, MissingArguments, UnknownCommand, UnexpectedError
from utils.logging import get_log_message, log_error


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

        if hasattr(error, "embed"):
            return await send_error(ctx, error.embed)

        if isinstance(error, DailyQuoteChannel):
            return

        if isinstance(error, commands.CommandNotFound):
            return await send_error(ctx, UnknownCommand.embed)

        await send_error(ctx, UnexpectedError(type(error).__name__).embed)

        log_message = get_log_message(ctx.message)
        log_error(log_message, error)


async def setup(bot):
    """Register the cog in the bot."""
    await bot.add_cog(ErrorHandler(bot))


async def send_error(ctx, embed):
    embed.color = ERROR
    await ctx.send(embed=embed)
