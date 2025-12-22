import aiohttp
import discord
from discord.ext import commands

from api.core import API_URL
from config import BOT_PREFIX, STAGING, STATS_CHANNEL_ID, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import get_user, update_commands, get_user_ids, get_all_command_usage
from utils.errors import UserBanned
from utils.files import get_command_modules
from utils.logging import get_log_message, log
from utils.messages import check_channel_permissions, welcome_message, command_milestone
from web_server.utils import get_nwpm_role_name

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
            # Assign verified role
            verified_role = discord.utils.get(member.guild.roles, name=VERIFIED_ROLE_NAME)
            if verified_role:
                await member.add_roles(verified_role)
                log(f"Assigned '{VERIFIED_ROLE_NAME}' role to {member.name}")

            # Fetch nWPM and assign role
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/user/{user_id}/nwpm") as response:
                    if response.status == 200:
                        data = await response.json()
                        nwpm = data.get("nwpm")

                        if nwpm is not None:
                            role_name = get_nwpm_role_name(nwpm)
                            if role_name:
                                nwpm_role = discord.utils.get(member.guild.roles, name=role_name)
                                if nwpm_role:
                                    await member.add_roles(nwpm_role)
                                    log(f"Assigned {role_name} nWPM role to {member.name}")

            # Assign GG+ role if applicable
            if user.get("isGgPlus"):
                gg_plus_role = discord.utils.get(member.guild.roles, name="GG+")
                if gg_plus_role:
                    await member.add_roles(gg_plus_role)
                    log(f"Assigned GG+ role to {member.name}")

        except Exception as e:
            log(f"Error reassigning roles to {member.name}: {e}")
