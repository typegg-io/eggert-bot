import importlib
import os
from typing import Optional

from discord import Embed
from discord.ext import commands

from config import bot_prefix as prefix
from database.users import get_user
from utils import errors, files

info = {
    "name": "help",
    "aliases": ["h"],
    "description": "Displays a list of available commands, or information about a specific command",
    "parameters": "[command]",
}

async def setup(bot):
    await bot.add_cog(Help(bot))

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def help(self, ctx, command: Optional[str] = None):
        bot_user = get_user(ctx.author.id)

        if not command:
            return await help_main(ctx, bot_user)

        return await help_command(ctx, bot_user, command)

async def help_main(ctx: commands.Context, bot_user: dict):
    description = (
        f"Use `{prefix}help [command]` to get information about a specific command.\n\n"
        f"**Parameter Notation:**\n"
        f"• Parameters in `[]` are optional\n"
        f"• Parameters in `<>` are required\n"
        f"• Parameters with `|` indicate a choice between options"
    )

    embed = Embed(
        title="Command Help",
        description=description,
        color=bot_user["theme"]["embed"],
    )

    groups = files.get_command_groups()
    for group in groups:
        command_list = []
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_") and not file.startswith("help"):
                command_list.append(file[:-3])
        command_list.sort()
        embed.add_field(
            name=f"{group.title()} Commands",
            value=", ".join(f"`{command}`" for command in command_list),
            inline=False
        )

    embed.set_footer(text="Developed by @keegant", icon_url="https://cdn.discordapp.com/avatars/155481579005804544/33ede24295683bbb2253481d5029266e.webp?size=1024")

    await ctx.send(embed=embed)


async def help_command(ctx: commands.Context, bot_user: dict, command_name: str):
    groups = files.get_command_groups()
    command = None
    for group in groups:
        for file in os.listdir(f"./commands/{group}"):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                command_info = module.info
                if command_name in [command_info["name"]] + command_info["aliases"]:
                    command = command_info
                    break

    if not command:
        return await ctx.send(embed=errors.unknown_command())

    name = command["name"]
    aliases = command["aliases"]

    embed = Embed(
        title=f"Help: `{prefix}{name}`",
        description=command["description"],
        color=bot_user["theme"]["embed"]
    )

    if "parameters" in command:
        parameter_string = f"`{prefix}{name}"
        if command["parameters"]:
            parameter_string += " " + command["parameters"]
        parameter_string += "`"
        if "defaults" in command:
            for param, default in command["defaults"].items():
                parameter_string += f"\n`{param}` defaults to {default}"
        embed.add_field(
            name="Usage",
            value=parameter_string,
            inline=False,
        )

    if "usage" in command:
        embed.add_field(
            name="Usage",
            value="\n".join([f"`{prefix}{usage}`" for usage in command['usage']]),
            inline=False,
        )

    if aliases:
        embed.add_field(
            name="Aliases",
            value=", ".join([f"`{prefix}{alias}`" for alias in aliases]),
            inline=False
        )

    await ctx.send(embed=embed)
