import asyncio

import discord
from discord import Embed
from discord.ext import commands

from config import bot_prefix as prefix, TYPEGG_GUILD_ID
from database.users import get_user, unlink_user
from utils.errors import RED

info = {
    "name": "unlink",
    "aliases": ["unverify"],
    "description": "Removes the link between your Discord account and your TypeGG account",
    "parameters": "",
}


async def setup(bot: commands.Bot):
    await bot.add_cog(Unlink(bot))


class Unlink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def unlink(self, ctx):
        bot_user = get_user(ctx.author.id)

        if not bot_user["user_id"]:
            return await ctx.send(embed=not_verified())

        await ctx.author.send(embed=Embed(
            title="Are You Sure?",
            description="You are about to remove the verificaton link\n"
                        "between your Discord and TypeGG account.\n"
                        "Please type \"confirm\" to proceed.",
            color=0XFFC107,
        ))

        def check(message):
            return message.author == ctx.author and message.content.lower() == "confirm"

        try:
            await self.bot.wait_for("message", timeout=10, check=check)
        except asyncio.TimeoutError:
            return
        else:
            await unverify_user(self.bot, ctx.author.id)
            unlink_user(ctx.author.id)

            embed = Embed(
                title="Verification Removed",
                description=f"To re-verify your account, run `{prefix}link`.\n",
                color=bot_user["theme"]["embed"]
            )

            await ctx.author.send(embed=embed)


async def unverify_user(bot_instance: commands.Bot, discord_id: str):
    guild = bot_instance.get_guild(TYPEGG_GUILD_ID)
    member = guild.get_member(int(discord_id))
    role = discord.utils.get(guild.roles, name="verified egg 🥚")

    await member.remove_roles(role)


def not_verified():
    return Embed(
        title="Not Verified",
        description="Your account has not yet been verified.",
        color=RED
    )
