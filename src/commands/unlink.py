import asyncio

import discord
from discord import Embed
from discord.ext import commands

from config import bot_prefix as prefix, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
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
    print(f"DEBUG: Looking for guild with ID {TYPEGG_GUILD_ID}")
    print(f"DEBUG: Bot has {len(bot_instance.guilds)} guilds")
    for g in bot_instance.guilds:
        print(f"DEBUG: Guild: {g.name} (ID: {g.id})")

    guild = bot_instance.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        print(f"ERROR: Guild with ID {TYPEGG_GUILD_ID} not found")
        return

    print(f"DEBUG: Found guild: {guild.name}")
    print(f"DEBUG: Looking for member with ID {discord_id}")
    print(f"DEBUG: Guild has {guild.member_count} members")

    member = guild.get_member(int(discord_id))
    if not member:
        print(f"ERROR: Member with ID {discord_id} not found in guild {guild.name}")
        return

    print(f"DEBUG: Found member: {member.name}")
    print(f"DEBUG: Looking for role '{VERIFIED_ROLE_NAME}'")
    print(f"DEBUG: Guild has {len(guild.roles)} roles")
    for r in guild.roles:
        print(f"DEBUG: Role: {r.name} (ID: {r.id})")

    role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if not role:
        print(f"ERROR: Role '{VERIFIED_ROLE_NAME}' not found in guild {guild.name}")
        return

    print(f"DEBUG: Found role: {role.name}")
    try:
        await member.remove_roles(role)
        print(f"SUCCESS: Removed {VERIFIED_ROLE_NAME} role from {member.name}")
    except discord.errors.Forbidden:
        print(f"ERROR: Bot lacks permission to remove {VERIFIED_ROLE_NAME} role from {member.name}")
    except Exception as e:
        print(f"ERROR: Error removing {VERIFIED_ROLE_NAME} role from {member.name}: {e}")


def not_verified():
    return Embed(
        title="Not Verified",
        description="Your account has not yet been verified.",
        color=RED
    )
