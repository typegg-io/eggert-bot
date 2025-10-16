import asyncio

import discord
from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX, BOT_TOKEN, STAGING, STATS_CHANNEL_ID
from database.bot.users import get_user_ids, get_all_command_usage, update_commands
from utils.files import get_command_modules, clear_image_cache
from utils.logging import get_log_message, log
from utils.messages import welcome_message, command_milestone
from watcher import start_watcher

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    case_insensitive=True,
    intents=intents,
)
bot.remove_command("help")

# Globals
users = get_user_ids()
total_commands = sum(get_all_command_usage().values())


# Event handlers
@bot.event
async def on_message(message: discord.Message):
    if (
        message.content.startswith(BOT_PREFIX)
        and not message.author.bot
        and not STAGING
    ):
        log_message = get_log_message(message)
        log(log_message)

        if message.author.id not in users:
            users.append(message.author.id)
            return await message.reply(content=welcome_message)

    await bot.process_commands(message)


@bot.event
async def on_command_completion(ctx: commands.Context):
    global total_commands

    command_origin = "server" if ctx.guild else "dm"
    update_commands(ctx.author.id, ctx.command.name, command_origin)

    total_commands += 1
    if total_commands % 50_000 == 0:
        await celebrate_milestone(ctx, total_commands)


async def celebrate_milestone(ctx: commands.Context, milestone: int):
    channel = bot.get_channel(STATS_CHANNEL_ID)
    if channel:
        await channel.send(embed=command_milestone(ctx.author.id, milestone))


# Lifecycle
@bot.event
async def on_ready():
    await load_commands()
    await bot.load_extension("error_handler")

    if not STAGING:
        await bot.load_extension("tasks")
        await bot.load_extension("web_server")
    else:
        loop = asyncio.get_running_loop()
        start_watcher(bot, loop)

    log("Bot ready.")


# Utilities
async def load_commands():
    for group, file, module in get_command_modules():
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                await bot.add_cog(obj(bot))
                break


# Entry point
if __name__ == "__main__":
    clear_image_cache()
    bot.run(BOT_TOKEN)
