import discord
from discord.ext import commands

from config import BOT_PREFIX, STAGING, STATS_CHANNEL_ID, TYPEGG_GUILD_ID
from database.bot.users import get_user, update_commands, get_user_ids, get_all_command_usage
from utils.errors import UserBanned, InvalidNumber
from utils.files import get_command_modules
from utils.flags import FLAG_VALUES, Flags, Language
from utils.logging import get_log_message, log
from utils.messages import check_channel_permissions, welcome_message, command_milestone
from utils.strings import get_argument, parse_number
from web_server.utils import assign_user_roles

users = get_user_ids()
total_commands = sum(get_all_command_usage().values())


def parse_flags(content: str) -> tuple[dict, str]:
    """Parse flags from message content. Returns (flags dict, cleaned command)."""
    invoke, raw_args = content.split()[0], content.split()[1:]

    flags = Flags()
    regular_args = []

    for arg in raw_args:
        if arg.startswith("-"):
            try:
                number = parse_number(arg.lstrip("-"))
                flags.number = number
                continue
            except InvalidNumber:
                pass

            flag = get_argument(FLAG_VALUES, arg.lstrip("-"), _raise=False)

            if not flag:
                regular_args.append(arg)
                continue

            match flag:
                case "pp" | "wpm":
                    flags.metric = flag
                case "raw":
                    flags.raw = True
                case "solo" | "quickplay" | "lobby":
                    flags.gamemode = flag
                case "ranked" | "unranked" | "any":
                    flags.status = flag
                case _:
                    flags.language = Language(flag)
        else:
            regular_args.append(arg)

    if flags.language:
        flags.status = "unranked"

    cleaned_command = f"{invoke} " + " ".join(regular_args)
    return flags, cleaned_command


async def load_commands(bot):
    """Load all command cogs into the bot."""
    from commands.base import Command

    for group, file, module in get_command_modules():
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                await bot.add_cog(obj(bot))
                break


def register_bot_checks(bot):
    """Register global bot checks and event handlers."""

    @bot.check
    async def set_user(ctx: commands.Context):
        """Attach a user to the context and block banned users."""
        ctx.flags = ctx.message.flags

        if not check_channel_permissions(ctx):
            return False

        if not hasattr(ctx, "user"):
            ctx.user = get_user(str(ctx.author.id))
            ctx.user["theme"]["isGgPlus"] = ctx.user["isGgPlus"]
        if ctx.user["isBanned"]:
            raise UserBanned("Banned user attempted to use a command")
        return True

    @bot.event
    async def on_message(message):
        """Global message handler."""

        if not message.content.startswith(BOT_PREFIX) or message.author.bot:
            return

        # Parsing flags
        flags, cleaned_command = parse_flags(message.content)
        message.flags = flags
        message.content = cleaned_command

        # Logging
        if not STAGING:
            log_message = get_log_message(message)
            log(log_message)

            # New users
            if message.author.id not in users:
                users.append(message.author.id)
                if not message.content.startswith(("-link", "-verify")):
                    return await message.reply(content=welcome_message)

        await bot.process_commands(message)

    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        """Re-process edited messages as commands."""
        if before.content == after.content:
            return

        if not after.content.startswith(BOT_PREFIX) or after.author.bot:
            return

        age = (discord.utils.utcnow() - after.created_at).total_seconds()
        if age > 20:
            return

        flags, cleaned_command = parse_flags(after.content)
        after.flags = flags
        after.content = cleaned_command

        await bot.process_commands(after)

    @bot.event
    async def on_command_completion(ctx: commands.Context):
        global total_commands

        command_origin = "server" if ctx.guild else "dm"
        update_commands(ctx.author.id, ctx.command.name, command_origin)

        total_commands += 1
        if total_commands % 50_000 == 0:
            channel = bot.get_channel(STATS_CHANNEL_ID)
            if channel:
                await channel.send(embed=command_milestone(ctx.author.id, total_commands))

    @bot.event
    async def on_member_join(member: discord.Member):
        """Reassign roles to linked users who rejoin the server."""
        if member.guild.id != TYPEGG_GUILD_ID:
            return

        user = get_user(str(member.id), auto_insert=False)
        if not user or not user.get("userId"):
            return

        user_id = user["userId"]
        log(f"Rejoining linked user detected: {member.name} (userId: {user_id})")

        try:
            await assign_user_roles(bot, member.guild, member.id, user_id)
        except Exception as e:
            log(f"Error reassigning roles to {member.name}: {e}")
