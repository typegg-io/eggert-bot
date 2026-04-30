from urllib.parse import quote

import aiohttp
from discord import Embed
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from utils.colors import ERROR
from utils.errors import MissingArguments
from utils.messages import Message, Page

info = {
    "name": "calculator",
    "aliases": ["cc", "eval", "math"],
    "description": "Evaluates a mathematical expression.\nUses https://api.mathjs.org/",
    "parameters": "[expression]",
    "examples": [
        "-cc 2 + 2",
        "-cc 1000 / 3",
    ],
}


class Calculator(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    async def calculator(self, ctx: BotContext):
        if not ctx.raw_args:
            raise MissingArguments

        encoded_expression = quote(" ".join(ctx.raw_args))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.mathjs.org/v4/?expr={encoded_expression}") as response:
                    result = await response.text()

                    if "Error" in result:
                        message = Message(ctx, Page(
                            title="Invalid Expression",
                            description="Expression format is invalid",
                            color=ERROR,
                        ))
                        return await message.send()

                    embed = Embed(
                        title="Calculator",
                        description=f"```{result}```",
                        color=ctx.user["theme"]["embed"],
                    )
                    await ctx.send(embed=embed)

        except aiohttp.ClientError:
            message = Message(ctx, Page(
                title="Calculator Error",
                description="Failed to connect to calculator service",
                color=ERROR,
            ))
            await message.send()
