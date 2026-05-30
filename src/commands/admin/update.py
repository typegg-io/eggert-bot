import asyncio

from discord import Embed
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from commands.checks import is_bot_owner
from utils.messages import Page, Message

info = {
    "name": "update",
    "aliases": [],
    "description": "Runs the update script to pull the latest changes and restart the bot.",
}


class Update(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def update(self, ctx: BotContext):
        message = Message(ctx, Page(title="Updating..."))
        await message.send()

        proc = await asyncio.create_subprocess_shell(
            "update",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines = []
        try:
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=15)
                if not line:
                    break
                output_lines.append(line.decode())
        except (asyncio.TimeoutError, Exception):
            pass

        output = "".join(output_lines).strip()
        if output:
            await message.message.edit(embed=Embed(
                title="Restarting...",
                description=f"```\n{output[:1900]}\n```",
            ))
