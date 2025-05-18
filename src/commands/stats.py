from typing import Optional

from discord import Embed
from discord.ext import commands

from api.users import get_profile
from database.users import get_user
from utils import errors
from utils.strings import discord_timestamp

info = {
    "name": "stats",
    "aliases": ["s"],
    "description": "Displays stats about a TypeGG account",
    "parameters": "[username]",
}


async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def stats(self, ctx, username: Optional[str] = "me"):
        bot_user = get_user(ctx.author.id)

        if username == "me":
            username = bot_user["user_id"]
        if not username:
            return await ctx.send(embed=errors.missing_arguments(info))

        await run(ctx, bot_user, username)


async def run(ctx: commands.Context, bot_user: dict, username: str):
    stats = await get_profile(username)

    embed = Embed(
        title="Profile",
        color=bot_user["theme"]["embed"],
    )

    general_field = f"Joined: {discord_timestamp(stats['joined'])}"
    country = stats["country"]
    if country:
        general_field += f"\nCountry: :flag_{country}: {country.upper()}"

    stats_field = (
        f"Global Ranking: #{stats['global_ranking']}\n"
        f"Total pp: {stats['total_pp']}\n"
        f"Highest WPM: {stats['highest_wpm']}\n"
        f"Highest pp: {stats['highest_pp']}\n"
    )

    embed.add_field(name="General", value=general_field, inline=False)
    embed.add_field(name="Stats", value=stats_field, inline=False)

    embed.set_thumbnail(url=stats["avatar"])
    embed.set_author(name=username)

    await ctx.send(embed=embed)
