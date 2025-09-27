import asyncio
import glob
import importlib
import os
import threading

import discord
from discord.ext import commands
from watchdog.observers import Observer

from commands.base import Command
from config import BOT_PREFIX, BOT_TOKEN, STAGING, TYPEGG_CHANNEL_ID, SOURCE_DIR
from database.bot.users import get_user_ids, get_total_commands, update_commands
from utils import files
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

total_commands = sum(get_total_commands().values())
users = get_user_ids()


@bot.event
async def on_message(message):
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
    channel = bot.get_channel(TYPEGG_CHANNEL_ID)
    await channel.send(embed=command_milestone(ctx.author.id, milestone))


@bot.event
async def on_ready():
    await load_commands()
    await bot.load_extension("error_handler")
    if not STAGING:
        await start_web_server(bot)
    else:
        loop = asyncio.get_running_loop()
        start_watcher(bot, loop)
    log("Bot ready.")


async def load_commands():
    groups = files.get_command_groups()
    for group in groups:
        for file in os.listdir(SOURCE_DIR / "commands" / group):
            if file.endswith(".py") and not file.startswith("_"):
                module_path = f"commands.{group}.{file[:-3]}"
                module = importlib.import_module(module_path)
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
