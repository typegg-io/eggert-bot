import importlib
import os
from typing import Optional

from discord import Embed
from discord.ext import commands

from config import bot_prefix as prefix
from database.users import get_user
from utils import errors

info = {
    "name": "help",
    "aliases": ["h"],
    "description": "Displays a list of available commands, or information about a specific command",
    "parameters": "<command>",
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def help(self, ctx, command: Optional[str] = None):
        bot_user = get_user(ctx.author.id)

        if not command:
            return await help_main(ctx, bot_user)

        command_dict = {}
        for file in os.listdir(f"./commands"):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{file[:-3]}")
                command_info = module.info
                for alias in [command_info["name"]] + command_info["aliases"]:
                    command_dict[alias] = command_info

        if command not in command_dict.keys():
            return await ctx.send(embed=errors.unknown_command())

        command = command_dict[command]
        await help_command(ctx, bot_user, command)


async def help_main(ctx: commands.Context, bot_user: dict):
    description = (
        f"`{prefix}help` - Displays this message\n"
        f"`{prefix}help [command]` - Displays help for a specific command\n"
        f"`[ ]` represents required parameters\n"
        f"`< >` represents optional parameters"
    )

    embed = Embed(
        title="Help Page",
        description=description,
        color=bot_user["theme"]["embed"],
    )

    command_list = []
    for file in os.listdir(f"./commands"):
        if file.endswith(".py") and not file.startswith("_") and not file.startswith("help"):
            command_list.append(file[:-3])

    commands_string = ", ".join(f"`{command}`" for command in command_list)
    embed.add_field(name="Commands", value=commands_string, inline=False)

    await ctx.send(embed=embed)


async def help_command(ctx: commands.Context, bot_user: dict, command_info: dict):
    name = command_info["name"]
    aliases = command_info["aliases"]

    embed = Embed(
        title=f"Help for `{prefix}{name}`",
        description=command_info['description'],
        color=bot_user["theme"]["embed"]
    )

    if "parameters" in command_info:
        parameter_string = f"`{prefix}{name}"
        if command_info["parameters"]:
            parameter_string += " " + command_info['parameters']
        parameter_string += "`"

        embed.add_field(
            name="Parameters",
            value=parameter_string,
            inline=False,
        )

    if aliases:
        embed.add_field(
            name="Aliases",
            value=", ".join([f"`{prefix}{alias}`" for alias in command_info['aliases']]),
            inline=False
        )

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
