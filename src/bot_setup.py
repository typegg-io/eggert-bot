from discord.ext import commands

from config import BOT_PREFIX, STAGING, STATS_CHANNEL_ID
from database.bot.users import get_user, update_commands, get_user_ids, get_all_command_usage
from utils.errors import UserBanned
from utils.files import get_command_modules
from utils.logging import get_log_message, log
from utils.messages import check_channel_permissions, welcome_message, command_milestone

users = get_user_ids()
total_commands = sum(get_all_command_usage().values())


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

        # Logging
        if not STAGING:
            log_message = get_log_message(message)
            log(log_message)

            # New users
            if message.author.id not in users:
                users.append(message.author.id)
                if not message.content.startswith(("-link", "-verify")):
                    return await message.reply(content=welcome_message)

        # Parsing flags
        content = message.content
        invoke, raw_args = content.split()[0], content.split()[1:]

        from utils.strings import get_argument
        from commands.base import FLAGS

        flags = {}
        regular_args = []

        for arg in raw_args:
            if arg.startswith("-"):
                flag = get_argument(FLAGS, arg.lstrip("-"), _raise=False)

                if not flag:
                    regular_args.append(arg)
                    continue

                match flag:
                    case "raw":
                        flags["metric"] = flag
                    case "solo" | "multiplayer":
                        flags["gamemode"] = flag
                    case "unranked" | "any":
                        flags["status"] = flag
            else:
                regular_args.append(arg)

        message.flags = flags
        message.content = f"{invoke} " + " ".join(regular_args)

        await bot.process_commands(message)

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
