import asyncio
import subprocess

from discord import Embed
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.checks import is_bot_owner
from config import ROOT_DIR, STAGING
from context import BotContext
from utils.messages import Message, Page

info = CommandInfo(
    name="update",
    aliases=[],
    description="Pulls the latest changes and restarts the bot.",
)


async def run_git(*args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", "-c", "color.ui=always", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=ROOT_DIR,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode, stdout.decode().strip().replace("\x1b[m", "\x1b[0m")


class Update(Command):
    """Pull the latest changes and restart the bot."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    @is_bot_owner()
    async def update(self, ctx: BotContext):
        """Sync to origin/main, report the output, then restart. Does nothing on staging."""
        if STAGING:
            return

        message = Message(ctx, Page(title="Updating..."))
        await message.send()

        returncode, output = await run_git("fetch", "origin", "main")
        if returncode == 0:
            _, before = await run_git("rev-parse", "HEAD")
            # --keep follows force-pushes but refuses to discard uncommitted edits.
            returncode, reset = await run_git("reset", "--keep", "FETCH_HEAD")
            output += "\n" + reset
            if returncode == 0:
                _, diff = await run_git("diff", "--stat", "--summary", before, "HEAD")
                output += "\n" + (diff or "Already up to date.")
        output = output.strip()

        if returncode != 0:
            await message.message.edit(embed=Embed(title="Update Failed"))
            await ctx.send(f"```ansi\n{output[:1900]}\n```")
            return

        await message.message.edit(embed=Embed(title="Restarted"))
        await ctx.send(f"```ansi\n{output[:1900]}\n```")

        subprocess.Popen(
            ["sudo", "systemctl", "restart", "eggert-bot"],
            start_new_session=True,
        )
