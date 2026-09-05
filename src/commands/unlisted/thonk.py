import random

from discord import File
from discord.ext import commands
from thonk import generate_thonk

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from utils import files

info = CommandInfo(
    name="thonk",
    aliases=[],
    description="Randomly generates a thonk emote.",
    parameters="[seed]",
    examples=[
        "-thonk",
        "-thonk 1234",
    ],
)


class Thonk(Command):
    """Generate a random thonk emote."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    async def thonk(self, ctx: BotContext):
        """Read an optional seed from the raw args, then render a thonk."""
        seed = " ".join(ctx.raw_args).replace("`", "") if ctx.raw_args else None
        await run(ctx, seed)


async def run(ctx: BotContext, seed: str | None) -> None:
    """Render a thonk from the given seed, or a random one, and send it."""
    if not seed:
        seed = str(random.randint(0, 1_000_000_000))

    file_name = "thonk.png"
    generate_thonk(seed=seed, output_size=256).save(file_name)

    file = File(file_name, filename=file_name)
    await ctx.send(content=f"-# Seed: `{seed}`", file=file)

    files.remove_file(file_name)


async def setup(bot) -> None:
    """Register the cog through the discord.py extension loader."""
    await bot.add_cog(Thonk(bot))
