from urllib.parse import quote

import aiohttp
from discord import Embed
from discord.ext import commands

from commands.base import Command
from utils.colors import ERROR
from utils.messages import Message, Page

info = {
    "name": "calculator",
    "aliases": ["cc", "eval", "math"],
    "description": "Evaluates a mathematical expression",
    "parameters": "[expression]",
}


class Calculator(Command):
    @commands.command(aliases=info["aliases"])
    async def calculator(self, ctx: commands.Context, *, expression: str):
        encoded_expression = quote(expression)

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
