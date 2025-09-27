import importlib
import os
from typing import Optional

from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX as prefix, SOURCE_DIR
from utils import files
from utils.errors import admin_command, unknown_command
from utils.messages import Page, Message, Field

info = {
    "name": "help",
    "aliases": ["h"],
    "description": "Displays a list of available commands, or information about a specific command",
    "parameters": "[command]",
}


class Help(Command):
    @commands.command(aliases=info["aliases"])
    async def help(self, ctx: commands.Context, command: Optional[str] = None):
        if not command:
            return await help_main(ctx)

        return await help_command(ctx, command)


async def help_main(ctx: commands.Context):
    description = (
        f"Use `{prefix}help <command>` to get information about a specific command.\n\n"
        f"**Parameter Notation:**\n"
        f"• Parameters in `<>` are required\n"
        f"• Parameters in `[]` are optional\n"
        f"• Parameters with `|` indicate a choice between options"
    )

    fields = []
    groups = files.get_command_groups()
    for group in groups:
        if group == "admin" and not ctx.user["isAdmin"]:
            continue
        command_list = []
        for file in os.listdir(SOURCE_DIR / "commands" / group):
            if file.endswith(".py") and not file.startswith("_") and not file.startswith("help"):
                command_list.append(file[:-3])
        command_list.sort()
        fields.append(Field(
            title=f"{group.title()}",
            content=", ".join(f"`{command}`" for command in command_list),
        ))

    page = Page(
        title="Command Help",
        description=description,
        fields=fields,
        color=ctx.user["theme"]["embed"],
    )

    message = Message(
        ctx=ctx,
        page=page,
        footer="Developed by @keegant",
        footer_icon="https://cdn.discordapp.com/avatars/155481579005804544/33ede24295683bbb2253481d5029266e.webp?size=1024",
    )

    await message.send()


async def help_command(ctx: commands.Context, command_name: str):
    groups = files.get_command_groups()
    command = None
    for group in groups:
        for file in os.listdir(SOURCE_DIR / "commands" / group):
            if file.endswith(".py") and not file.startswith("_"):
                module = importlib.import_module(f"commands.{group}.{file[:-3]}")
                command_info = module.info
                if command_name in [command_info["name"]] + command_info["aliases"]:
                    if group == "admin" and not ctx.user["isAdmin"]:
                        return await ctx.send(embed=admin_command())
                    command = command_info
                    break

    if not command:
        return await ctx.send(embed=unknown_command())

    name = command["name"]
    aliases = command["aliases"]
    fields = []

    if "parameters" in command:
        parameter_string = f"`{prefix}{name}"
        if command["parameters"]:
            parameter_string += " " + command["parameters"]
        parameter_string += "`"
        if "defaults" in command:
            for param, default in command["defaults"].items():
                parameter_string += f"\n`{param}` defaults to {default}"
        fields.append(Field(
            title="Usage",
            content=parameter_string,
        ))

    if "usage" in command:
        fields.append(Field(
            title="Usage",
            content="\n".join([f"`{prefix}{usage}`" for usage in command["usage"]]),
        ))

    if aliases:
        fields.append(Field(
            title="Aliases",
            content=", ".join([f"`{prefix}{alias}`" for alias in aliases]),
        ))

    page = Page(
        title=f"Help: `{prefix}{name}`",
        description=command["description"],
        fields=fields,
        color=ctx.user["theme"]["embed"],
    )

    message = Message(
        ctx=ctx,
        page=page,
    )

    await message.send()
