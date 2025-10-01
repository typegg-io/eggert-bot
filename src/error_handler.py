import importlib

import discord
from discord.ext import commands

from utils.errors import UserBanned, unknown_command, MissingUsername, missing_arguments, unexpected_error, DailyQuoteChannel
from utils.logging import get_log_message, log_error


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, UserBanned):
            try:
                await ctx.author.send(embed=error.embed)
            except discord.Forbidden:
                pass
            return

        if hasattr(error, "embed"):
            return await ctx.send(embed=error.embed)

        if isinstance(error, DailyQuoteChannel):
            return

        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=unknown_command())

        if isinstance(error, (commands.MissingRequiredArgument, MissingUsername)):
            module_path = ctx.command.callback.__module__
            command_info = importlib.import_module(module_path).info
            return await ctx.send(
                embed=missing_arguments(
                    command_info,
                    show_tip=isinstance(error, MissingUsername)
                )
            )

        await ctx.send(embed=unexpected_error())

        log_message = get_log_message(ctx.message)
        log_error(log_message, error)


async def setup(bot):
    """Register the cog in the bot."""
    await bot.add_cog(ErrorHandler(bot))
