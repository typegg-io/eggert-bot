import asyncio

import discord
from discord import Embed
from discord.ext import commands

from commands.base import Command
from config import BOT_PREFIX, TYPEGG_GUILD_ID, VERIFIED_ROLE_NAME
from database.bot.users import unlink_user
from utils.colors import ERROR, WARNING
from utils.logging import log

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

        await ctx.send(embed=Embed(
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

            return await ctx.send(embed=embed)


async def unverify_user(bot_instance: commands.Bot, discord_id: str):
    guild = bot_instance.get_guild(TYPEGG_GUILD_ID)
    if not guild:
        log(f"Guild with ID {TYPEGG_GUILD_ID} not found")
        return

    member = guild.get_member(int(discord_id))
    if not member:
        log(f"Member with ID {discord_id} not found in guild {guild.name}")
        return

    roles_to_remove = []

    # Find verified role
    verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
    if verified_role and verified_role in member.roles:
        roles_to_remove.append(verified_role)

    # Find GG+ role
    gg_plus_role = discord.utils.get(guild.roles, name="GG+")
    if gg_plus_role and gg_plus_role in member.roles:
        roles_to_remove.append(gg_plus_role)

    # Find nWPM roles
    nwpm_roles = [
        role for role in member.roles
        if role.name == "250+" or (
            "-" in role.name and
            role.name.split("-")[0].isdigit() and
            role.name.split("-")[-1].isdigit()
        )
    ]
    roles_to_remove.extend(nwpm_roles)

    if not roles_to_remove:
        log(f"No roles to remove for {member.name}")
        return

    # Remove all roles
    try:
        await member.remove_roles(*roles_to_remove, reason="Unlinking account")
        role_names = ", ".join([role.name for role in roles_to_remove])
        log(f"Removed roles from {member.name}: {role_names}")
    except (discord.Forbidden, discord.HTTPException) as e:
        log(f"Failed to remove roles from {member.name}: {e}")


def not_verified():
    return Embed(
        title="Not Verified",
        description="Your account has not yet been verified.",
        color=ERROR
    )
