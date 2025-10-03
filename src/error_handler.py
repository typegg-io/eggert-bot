import importlib

import discord
from discord.ext import commands

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
                await ctx.author.send(embed=error.embed)
            except discord.Forbidden:
                pass
            return

        if isinstance(error, (commands.MissingRequiredArgument, MissingArguments, MissingUsername)):
            module_path = ctx.command.callback.__module__
            command_info = importlib.import_module(module_path).info
            print(MissingArguments().embed(command_info))
            missing_arguments = MissingArguments().embed(
                command_info,
                show_tip=isinstance(error, MissingUsername),
            )
            return await ctx.send(embed=missing_arguments)

        if hasattr(error, "embed"):
            return await ctx.send(embed=error.embed)

        if isinstance(error, DailyQuoteChannel):
            return

        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=UnknownCommand.embed)

        await ctx.send(embed=UnexpectedError(type(error).__name__).embed)

        log_message = get_log_message(ctx.message)
        log_error(log_message, error)


async def setup(bot):
    """Register the cog in the bot."""
    await bot.add_cog(ErrorHandler(bot))
