import asyncio

import discord
from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX, BOT_TOKEN, STAGING
from utils.files import get_command_modules, clear_image_cache
from utils.logging import log
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


# Lifecycle
@bot.event
async def on_ready():
    await load_commands()
    await bot.load_extension("error_handler")
    await bot.load_extension("web_server.server")

    if not STAGING:
        await bot.load_extension("tasks")
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
