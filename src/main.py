import asyncio

import discord
from discord.ext import commands

from bot_setup import load_commands, register_bot_checks
from config import BOT_PREFIX, BOT_TOKEN, STAGING
from utils.files import clear_image_cache
from utils.logging import log
from utils.nwpm_model import initialize_nwpm_model
from watcher import start_watcher

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


@bot.event
async def on_ready():
    await load_commands(bot)
    register_bot_checks(bot)
    await bot.load_extension("error_handler")
    await bot.load_extension("web_server.server")
    await initialize_nwpm_model()

    if not STAGING:
        await bot.load_extension("tasks")
    else:
        loop = asyncio.get_running_loop()
        start_watcher(bot, loop)

    log("Bot ready.")


if __name__ == "__main__":
    clear_image_cache()
    bot.run(BOT_TOKEN)
