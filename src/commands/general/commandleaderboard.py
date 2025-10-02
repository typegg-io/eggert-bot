from typing import Optional

from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX
from database.bot.users import get_command_usage_by_user, get_top_users_by_command_usage, get_all_command_usage, get_command_usage
from utils.errors import UnknownCommand, BotUserNotFound
from utils.files import get_command_modules
from utils.messages import Page, Message

info = {
    "name": "commandleaderboard",
    "aliases": ["clb", "blb"],
    "description": "Displays command usage stats for a specific command or user\n"
                   f"`{BOT_PREFIX}commandleaderboard all` will show most use commands overall",
    "parameters": "[command_name|discord_id]",
}


class CommandLeaderboard(Command):
    @commands.command(aliases=info["aliases"])
    async def commandleaderboard(self, ctx: commands.Context, arg: Optional[str] = None):
        if not arg:
            return await user_command_leaderboard(ctx, ctx.author.id)

        command_aliases = {}
        for group, file, module in get_command_modules():
            command_name = module.info["name"]
            aliases = [command_name] + module.info["aliases"]
            for alias in aliases:
                command_aliases[alias] = command_name

        if arg in command_aliases:
            await command_leaderboard(ctx, command_aliases[arg])

        elif arg in ["users", "all"]:
            await user_command_leaderboard(ctx, arg)

        else:
            try:
                member = await commands.MemberConverter().convert(ctx, arg)
                await user_command_leaderboard(ctx, member.id)
            except commands.BadArgument:
                raise UnknownCommand


async def command_leaderboard(ctx: commands.Context, command_name: str):
    """Display a leaderboard of users by usage count for a given command."""
    all_commands = get_command_usage_by_user()

    command_usage = [user for user in all_commands if command_name in user["commands"]]
    total_usages = sum(user["commands"][command_name] for user in command_usage)
    sorted_usage = sorted(
        command_usage,
        key=lambda user: user["commands"][command_name],
        reverse=True,
    )

    description_lines = [
        f"{i + 1}. <@{user["discord_id"]}> - {user["commands"][command_name]:,}"
        for i, user in enumerate(sorted_usage[:10])
    ]
    description = "\n".join(description_lines) or ""

    page = Page(
        title=f"Usage Leaderboard - {command_name}",
        description=description,
        footer=f"Total Usages: {total_usages:,}",
    )

    message = Message(ctx, page=page)

    await message.send()


def format_user_leaderboard(top_users: list[dict]):
    description = "**Overall**\n\n"
    total_usages = sum(user["total_commands"] for user in top_users)
    for i, user in enumerate(top_users[:20]):
        description += f"{i + 1}. <@{user['discord_id']}> - {user['total_commands']:,}\n"
    return description, total_usages


def format_command_leaderboard(command_usage: dict, discord_id: int | str):
    description = f"<@{discord_id}>\n\n" if discord_id != "all" else "**Overall**\n\n"
    total_usages = sum(command_usage.values())
    most_used_commands = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)

    for i, (name, usages) in enumerate(most_used_commands[:10]):
        description += f"{i + 1}. {name} - {usages:,}\n"
    return description, total_usages


async def user_command_leaderboard(ctx: commands.Context, discord_id: int | str):
    """Display a leaderboard of command usage count by user, or overall."""
    if discord_id == "users":
        title = "Top Command Users"
        top_users = get_top_users_by_command_usage()
        description, total_usages = format_user_leaderboard(top_users)
        footer_text = f"Total Usages: {total_usages:,}\nTotal Users: {len(top_users):,}"
    else:
        title = "Most Used Commands"
        if discord_id == "all":
            command_usage = get_all_command_usage()
        else:
            command_usage = get_command_usage(discord_id)
            if not command_usage:
                raise BotUserNotFound(discord_id)

        description, total_usages = format_command_leaderboard(command_usage, discord_id)
        footer_text = f"Total Usages: {total_usages:,}"

    page = Page(title=title, description=description, footer=footer_text)
    message = Message(ctx, page=page)

    await message.send()
