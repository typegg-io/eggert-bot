from discord import Embed
from discord.ext import commands

info = {
    "name": "ping",
    "aliases": ["p"],
    "description": "Displays the bot's latency",
    "parameters": "",
}


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        embed = Embed(
            description=f"Pong! :ping_pong: {latency}ms",
        )
        await ctx.send(embed=embed)
