from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.bot.command_log import (
    get_all_command_usage,
    get_command_leaderboard,
    get_command_usage,
    get_top_users_by_command_usage,
)
from utils.errors import BotUserNotFound, UnknownCommand, UserNotAdmin
from utils.files import get_command_modules
from utils.messages import Message, Page

info = CommandInfo(
    name="commandleaderboard",
    aliases=["clb", "blb"],
    description="Displays your command usage breakdown.\n"
                "Pass a Discord user to see theirs.",
    parameters="[user]",
    examples=[
        "-clb",
        "-clb @user",
    ],
)


class CommandLeaderboard(Command):
    """Display command usage counts, by user or by command."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    async def commandleaderboard(self, ctx: BotContext):
        """Read the argument as a command name, a Discord user, or the overall keyword."""
        arg = " ".join(ctx.raw_args)
        if not arg:
            return await user_command_leaderboard(ctx, ctx.author.id)

        command_aliases = {}
        for group, file, module in get_command_modules():
            command_name = module.info.name
            for alias in module.info.all_names:
                command_aliases[alias] = command_name

        if arg in command_aliases:
            if not ctx.user["isAdmin"]:
                raise UserNotAdmin
            await command_leaderboard(ctx, command_aliases[arg])

        elif arg in ["users", "all"]:
            if arg == "users" and not ctx.user["isAdmin"]:
                raise UserNotAdmin
            await user_command_leaderboard(ctx, arg)

        else:
            try:
                user = await commands.UserConverter().convert(ctx, arg)
                await user_command_leaderboard(ctx, user.id)
            except commands.BadArgument:
                raise UnknownCommand


async def command_leaderboard(ctx: BotContext, command_name: str) -> None:
    """Display a leaderboard of users by usage count for a given command."""
    command_usage = get_command_leaderboard(command_name)
    total_usages = sum(user["usages"] for user in command_usage)

    description_lines = [
        f"{i + 1}. <@{user["discord_id"]}> - {user["usages"]:,}"
        for i, user in enumerate(command_usage[:10])
    ]
    description = "\n".join(description_lines) or ""

    page = Page(
        title=f"Usage Leaderboard - {command_name}",
        description=description,
        footer=f"Total Usages: {total_usages:,}",
    )

    message = Message(ctx, page=page)

    await message.send()


def format_user_leaderboard(top_users: list[dict]) -> tuple[str, int]:
    """Format the top 20 users by total command count, with the total alongside."""
    description = "**Overall**\n\n"
    total_usages = sum(user["total_commands"] for user in top_users)
    for i, user in enumerate(top_users[:20]):
        description += f"{i + 1}. <@{user['discord_id']}> - {user['total_commands']:,}\n"
    return description, total_usages


def format_command_leaderboard(command_usage: dict, discord_id: int | str) -> tuple[str, int]:
    """Format the 10 most used commands, with the total alongside."""
    description = f"<@{discord_id}>\n\n" if discord_id != "all" else "**Overall**\n\n"
    total_usages = sum(command_usage.values())
    most_used_commands = sorted(command_usage.items(), key=lambda x: x[1], reverse=True)

    for i, (name, usages) in enumerate(most_used_commands[:10]):
        description += f"{i + 1}. {name} - {usages:,}\n"
    return description, total_usages


async def user_command_leaderboard(ctx: BotContext, discord_id: int | str) -> None:
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
