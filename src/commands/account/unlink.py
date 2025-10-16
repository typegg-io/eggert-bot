import asyncio

import discord
from discord import Embed
from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import unlink_user
from utils.colors import ERROR, WARNING

info = {
    "name": "unlink",
    "aliases": ["unverify"],
    "description": "Removes the link between your Discord account and your TypeGG account",
}


class Unlink(Command):
    @commands.command(aliases=info["aliases"])
    async def unlink(self, ctx: commands.Context):
        if not ctx.user["userId"]:
            return await ctx.send(embed=not_verified())

        await ctx.author.send(embed=Embed(
            title="Are You Sure?",
            description=(
                "You are about to remove the verification link\n"
                "between your Discord and TypeGG account.\n"
                "Please type \"confirm\" to proceed."
            ),
            color=WARNING,
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
                description=f"To re-verify your account, run `{BOT_PREFIX}link`.\n",
                color=ctx.user["theme"]["embed"]
            )

            await ctx.author.send(embed=embed)


async def unverify_user(bot_instance: commands.Bot, discord_id: str):
    guild = bot_instance.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        print(f"Guild with ID {TYPEGG_GUILD_ID} not found")
        return

    member = guild.get_member(int(discord_id))
    if not member:
        print(f"Member with ID {discord_id} not found in guild {guild.name}")
        return

    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not role:
        print(f"Role '{VERIFIED_ROLE_NAME}' not found in guild {guild.name}")
        return

    try:
        await member.remove_roles(role)
        print(f"Removed {VERIFIED_ROLE_NAME} role from {member.name}")
    except discord.errors.Forbidden:
        print(f"Bot lacks permission to remove {VERIFIED_ROLE_NAME} role from {member.name}")
    except Exception as e:
        print(f"Error removing {VERIFIED_ROLE_NAME} role from {member.name}: {e}")


def not_verified():
    return Embed(
        title="Not Verified",
        description="Your account has not yet been verified.",
        color=ERROR
    )
