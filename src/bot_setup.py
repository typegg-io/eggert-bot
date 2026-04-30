import asyncio
import re
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord.ext import commands

from config import BOT_PREFIX, STAGING, STATS_CHANNEL_ID, TYPEGG_GUILD_ID, GENERAL_CHANNEL_ID, SITE_CHAT_URL, SECRET, SITE_URL
from database.bot.users import get_user, update_commands, get_user_ids, get_all_command_usage
from database.typegg.quotes import is_quote_id
from utils.dates import is_date_like, parse_date
from utils.errors import UserBanned, InvalidNumber
from utils.files import get_command_modules
from utils.flags import FLAG_VALUES, Flags, Language
from utils.logging import get_log_message, log
from utils.strings import get_argument, parse_number, parse_wpm_range
from web_server.utils import assign_user_roles

users = get_user_ids()
total_commands = sum(get_all_command_usage().values())


class BotContext(commands.Context):
    flags: Flags
    explicit_flags: dict[str, str]
    user: dict
    raw_args: tuple


class Eggert(commands.Bot):
    """
    Custom Bot subclass that intercepts message context to parse flags before command dispatch.

    Before discord.py resolves a command, get_context strips flag tokens (e.g. -ranked, -solo)
    from the message content and populates three extra fields on every BotContext:

    ctx.flags          - Flags dataclass with resolved values (metric, gamemode, status, etc.)
    ctx.explicit_flags - maps flag name -> original arg text, only for flags the user typed
    ctx.raw_args       - original tokens after the command name, before any stripping
    """

    async def get_context(self, message, *, cls=BotContext):
        if message.content.startswith(BOT_PREFIX):
            original_content = message.content
            flags, cleaned, explicit_flags = parse_flags(message.content)
            message.content = cleaned
            ctx = await super().get_context(message, cls=cls)
            message.content = original_content
        else:
            flags, explicit_flags = Flags(), {}
            ctx = await super().get_context(message, cls=cls)
        ctx.flags = flags
        ctx.explicit_flags = explicit_flags
        ctx.raw_args = tuple(ctx.message.content.split()[1:])
        return ctx


def parse_flags(content: str) -> tuple[Flags, str, dict[str, str]]:
    """Parse flags from message content. Returns (flags, cleaned command, explicit_flags).

    explicit_flags maps flag name -> original arg text the user typed,
    e.g. {"gamemode": "-solo", "raw": "-raw"}.
    """
    invoke, raw_args = content.split()[0], content.split()[1:]

    flags = Flags()
    explicit_flags: dict[str, str] = {}
    regular_args = []  # Non-flag arguments

    for arg in raw_args[::-1]:
        value = arg.lstrip("-")

        try:
            number = parse_number(value)
            if not (-2147483648 <= number <= 2147483647):
                raise InvalidNumber
            sign = -1 if arg.startswith("-") else 1
            flags.number = number * sign
            explicit_flags["number"] = arg
            continue
        except InvalidNumber:
            pass

        if is_date_like(value):
            flags.date = value
            explicit_flags["date"] = arg
            continue

        if wpm_range := parse_wpm_range(value):
            flags.number_range = wpm_range
            explicit_flags["number_range"] = arg
            continue

        flag = get_argument(FLAG_VALUES, value, _raise=False)
        if flag:
            match flag:
                case "pp" | "wpm":
                    flags.metric = flag
                    explicit_flags["metric"] = arg
                case "raw":
                    flags.raw = True
                    explicit_flags["raw"] = arg
                case "solo" | "quickplay" | "lobby":
                    flags.gamemode = flag
                    explicit_flags["gamemode"] = arg
                case "ranked" | "unranked" | "any":
                    flags.status = flag
                    explicit_flags["status"] = arg
                case _:
                    flags.language = Language(flag)
                    explicit_flags["language"] = arg
            continue

        if (
            arg in ["^", "daily"]
            or arg.startswith(f"{SITE_URL}/solo/")
            or is_quote_id(arg)
        ):
            flags.quote_id = value
            explicit_flags["quote_id"] = arg
            continue

        regular_args.append(arg)

    if flags.language:
        flags.status = "unranked"

    if flags.status != "ranked":
        flags.metric = "wpm"

    flags.date = parse_date(flags.date)

    cleaned_command = f"{invoke} " + " ".join(regular_args)
    return flags, cleaned_command, explicit_flags


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
    from utils.messages import check_channel_permissions

    @bot.check
    async def set_user(ctx: BotContext):
        """Attach a user to the context and block banned users."""
        if not check_channel_permissions(ctx):
            return False

        if not hasattr(ctx, "user"):
            ctx.user = get_user(str(ctx.author.id))
            ctx.user["theme"]["isGgPlus"] = ctx.user["isGgPlus"]
            ctx.user["timezone"] = ZoneInfo(ctx.user["timezone"])
        if ctx.user["isBanned"]:
            raise UserBanned("Banned user attempted to use a command")
        return True

    async def forward_to_site(message):
        """Forward a general channel message to the site's chat."""
        user = get_user(str(message.author.id), auto_insert=False)
        linked = user and user.get("userId")
        guild = message.guild

        def replace_mention(m):
            uid = int(m.group(1))
            mentioned_user = get_user(str(uid), auto_insert=False)
            if mentioned_user:
                return f"<@{mentioned_user["userId"]}>"
            member = guild.get_member(uid) if guild else None
            return f"@{member.name}" if member else "@unknown"

        def replace_role(m):
            rid = int(m.group(1))
            role = guild.get_role(rid) if guild else None
            return f"@{role.name}" if role else "@unknown"

        def replace_channel(m):
            cid = int(m.group(1))
            channel = guild.get_channel(cid) if guild else None
            return f"#{channel.name}" if channel else "#unknown"

        content = re.sub(r"<a?:(\w+):\d+>", r":\1:", message.content)  # custom emojis -> :name:
        content = re.sub(r"<@!?(\d+)>", replace_mention, content)  # user mentions -> @username or <@tggId>
        content = re.sub(r"<@&(\d+)>", replace_role, content)  # role mentions -> @Role
        content = re.sub(r"<#(\d+)>", replace_channel, content)  # channels -> #channel
        content = re.sub(r"<(?!@)\S+>", "", content)  # strip unrecognized tags
        content = content.strip()
        if not content:
            return

        payload = {
            "username": message.author.name,
            "avatarUrl": message.author.display_avatar.url,
            "content": content,
        }
        if linked:
            payload |= {"userId": user["userId"]}

        async with aiohttp.ClientSession() as session:
            await session.post(
                SITE_CHAT_URL,
                json=payload,
                headers={"Authorization": SECRET},
            )

    @bot.event
    async def on_message(message):
        """Global message handler."""
        from utils.messages import welcome_message

        if message.author.bot:
            return

        if SITE_CHAT_URL and message.channel.id == GENERAL_CHANNEL_ID and not message.content.startswith(BOT_PREFIX):
            asyncio.ensure_future(forward_to_site(message))  # Fire and forget
            return

        if not message.content.startswith(BOT_PREFIX):
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

        await bot.process_commands(after)

    @bot.event
    async def on_command_completion(ctx: BotContext):
        from utils.messages import command_milestone
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
