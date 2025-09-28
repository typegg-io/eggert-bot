import importlib

import discord
from discord.ext import commands

from utils import errors
from utils.logging import get_log_message, log_error


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, errors.UserBanned):
            try:
                await ctx.author.send(embed=errors.banned_user())
            except discord.Forbidden:
                pass
            return

        if isinstance(error, errors.UserNotAdmin):
            return await ctx.send(embed=errors.admin_command())

        if isinstance(error, errors.UserNotOwner):
            return await ctx.send(embed=errors.owner_command())

        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=errors.unknown_command())

        if isinstance(error, (commands.MissingRequiredArgument, errors.MissingUsername)):
            module_path = ctx.command.callback.__module__
            command_info = importlib.import_module(module_path).info
            return await ctx.send(
                embed=errors.missing_arguments(
                    command_info,
                    show_tip=isinstance(error, errors.MissingUsername)
                )
            )

        if isinstance(error, errors.ProfileNotFound):
            return await ctx.send(embed=errors.invalid_user(error.username))

        if isinstance(error, errors.NoRaces):
            return await ctx.send(embed=errors.no_races(error.username))

        await ctx.send(embed=errors.unexpected_error())

        log_message = get_log_message(ctx.message)
        log_error(log_message, error)


async def setup(bot):
    """Register the cog in the bot."""
    await bot.add_cog(ErrorHandler(bot))
