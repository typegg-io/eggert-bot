import asyncio
import glob
import os
import threading

import discord
from discord.ext import commands, tasks
from watchdog.observers import Observer

from commands.base import Command
from config import BOT_PREFIX, BOT_TOKEN, STAGING, STATS_CHANNEL_ID, SOURCE_DIR, DAILY_QUOTE_CHANNEL_ID
from database.bot.users import get_user_ids, get_all_command_usage, update_commands
from tasks import daily_quote_ping
from utils import dates
from utils.files import get_command_modules
from utils.logging import get_log_message, log
from utils.messages import welcome_message, command_milestone
from watcher import ReloadHandler
from web_server import start_web_server

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix=BOT_PREFIX, case_insensitive=True, intents=intents)
bot.remove_command("help")

total_commands = sum(get_all_command_usage().values())
users = get_user_ids()


@bot.event
async def on_message(message):
    if message.channel.id == DAILY_QUOTE_CHANNEL_ID:
        return

    if message.content.startswith(BOT_PREFIX) and not message.author.bot and not STAGING:
        log_message = get_log_message(message)
        log(log_message)
        user_id = message.author.id
        if user_id not in users:
            users.append(user_id)
            return await message.reply(content=welcome_message)

    await bot.process_commands(message)


@bot.event
async def on_command_completion(ctx):
    global total_commands
    command_origin = "server" if ctx.guild else "dm"
    update_commands(ctx.author.id, ctx.command.name, command_origin)
    total_commands += 1
    if total_commands % 50_000 == 0:
        await celebrate_milestone(ctx, total_commands)


async def celebrate_milestone(ctx, milestone):
    channel = bot.get_channel(STATS_CHANNEL_ID)
    await channel.send(embed=command_milestone(ctx.author.id, milestone))


@bot.event
async def on_ready():
    await load_commands()
    await bot.load_extension("error_handler")
    if not STAGING:
        tasks.start()
        await start_web_server(bot)
    else:
        loop = asyncio.get_running_loop()
        start_watcher(bot, loop)
    log("Bot ready.")


@tasks.loop(minutes=1)
async def tasks():
    now = dates.now()
    if now.hour == 0 and now.minute == 5:
        await daily_quote_ping(bot)


async def load_commands():
    for group, file, module in get_command_modules():
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, Command) and obj is not Command:
                await bot.add_cog(obj(bot))
                break


def start_watcher(bot, loop):
    observer = Observer()
    observer.schedule(ReloadHandler(bot, loop), path=SOURCE_DIR / "commands", recursive=True)
    thread = threading.Thread(target=observer.start, daemon=True)
    thread.start()


def clear_image_cache():
    images = glob.glob("*.png")
    for file in images:
        os.remove(file)


if __name__ == "__main__":
    clear_image_cache()
    bot.run(BOT_TOKEN)
