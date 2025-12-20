from typing import Optional

from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX as prefix
from utils import files
from utils.errors import UnknownCommand, UserNotAdmin
from utils.files import get_command_modules
from utils.messages import Page, Message, Field
from utils.strings import GG_PLUS

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
        f"• Parameters with `|` indicate a choice between options\n"
        f"**Parameter Flags**\n"
        f"• Metric: `-raw`\n"
        f"• Gamemode: `-solo`, `-multi`\n"
        f"• Status: `-unranked`, `-any`\n"
    )

    fields = []
    groups = files.get_command_groups()

    modules_by_group = {}
    for group, file, module in get_command_modules():
        if group not in modules_by_group:
            modules_by_group[group] = []
        modules_by_group[group].append(module)

    for group in groups:
        if group == "unlisted":
            continue
        if group == "admin" and not ctx.user["isAdmin"]:
            continue

        commands = []
        if group in modules_by_group:
            for module in modules_by_group[group]:
                command_info = module.info
                commands.append((command_info["name"], command_info.get("plus", False)))

        commands.sort(key=lambda x: x[0])

        command_list = []
        for name, is_plus in commands:
            if is_plus:
                command_list.append(f"`{name}` {GG_PLUS}")
            else:
                command_list.append(f"`{name}`")

        fields.append(Field(
            title=f"{group.title()}",
            content=", ".join(command_list),
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
    command = None
    for group, file, module in get_command_modules():
        command_info = module.info
        if command_name in [command_info["name"]] + command_info["aliases"]:
            if group == "admin" and not ctx.user["isAdmin"]:
                raise UserNotAdmin
            command = command_info
            break

    if not command:
        raise UnknownCommand

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

    command_author = command.get("author", None)
    if command_author:
        fields.append(Field(
            title="\t",
            content=f"-# Command by <@{command_author}>"
        ))

    if command.get("plus"):
        fields.append(Field(
            title="\t",
            content=f"{GG_PLUS} exclusive"
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
