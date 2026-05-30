import asyncio
import subprocess

from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from config import ROOT_DIR, STAGING
from utils.messages import Page, Message

info = {
    "name": "update",
    "aliases": [],
    "description": "Pulls the latest changes and restarts the bot.",
}


class Update(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def update(self, ctx: BotContext):
        if STAGING:
            return

        message = Message(ctx, Page(title="Updating..."))
        await message.send()

        proc = await asyncio.create_subprocess_exec(
            "git", "pull", "origin", "main",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=ROOT_DIR,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode().strip()

        await message.message.edit(content="Restarted", embed=None)
        await ctx.send(f"```\n{output[:1900]}\n```")

        subprocess.Popen(
            ["sudo", "systemctl", "restart", "eggert-bot"],
            start_new_session=True,
        )
