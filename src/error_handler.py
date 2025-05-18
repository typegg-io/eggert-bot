import importlib

from discord.ext import commands

from utils import errors


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return await ctx.send(embed=errors.unknown_command())

        if isinstance(error, commands.MissingRequiredArgument):
            command_info = importlib.import_module(f"commands.{ctx.command.name}").info
            return await ctx.send(embed=errors.missing_arguments(command_info))

        await ctx.send(embed=errors.unexpected_error())

        print(f"Unhandled error: {error}")


# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
