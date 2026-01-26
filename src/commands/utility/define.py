import aiohttp
from discord import Embed
from discord.ext import commands

from commands.base import Command
from utils.colors import ERROR
from utils.errors import MissingArguments

info = {
    "name": "define",
    "aliases": ["def"],
    "description": "Displays the definition(s) of a word",
    "parameters": "[word]",
}


class Define(Command):
    @commands.command(aliases=info["aliases"])
    async def define(self, ctx, *words: str):
        if not words:
            raise MissingArguments

        word = words[0]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.dictionaryapi.dev/api/v2/entries/en/" + word) as response:
                    result = await response.json()

                    if "title" in result:
                        return await ctx.send(embed=Embed(
                            title="Unknown Word",
                            description="Sorry, I don't know this word",
                            color=ERROR,
                        ))

                    definitions = result[0]["meanings"]

                    description = ""
                    for group in definitions:
                        part = group["partOfSpeech"].title()
                        description += f"**{part}**\n"
                        for definition in group["definitions"]:
                            description += "\\- " + definition["definition"] + "\n"
                        description += "\n"

                    embed = Embed(
                        title=word.capitalize() + " - Definition",
                        description=description,
                        color=ctx.user["theme"]["embed"],
                    )

                    await ctx.send(embed=embed)

        except aiohttp.ClientError:
            return await ctx.send(embed=Embed(
                title="Dictionary Error",
                description="Failed to connect to dictionary service",
                color=ERROR,
            ))
