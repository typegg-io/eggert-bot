from typing import Optional

from discord import Embed
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from utils.colors import ERROR

info = {
    "name": "profilepicture",
    "aliases": ["avatar", "pfp"],
    "description": "Displays a user's TypeGG profile picture.",
    "parameters": "[username]",
    "examples": [
        "-pfp",
        "-pfp eiko",
    ],
}


class ProfilePicture(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    async def profilepicture(self, ctx: BotContext, username: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=False)
        await run(ctx, profile)


def no_profile_picture():
    return Embed(
        title="No Profile Picture",
        description="User does not have a profile picture",
        color=ERROR,
    )


async def run(ctx: BotContext, profile: dict):
    avatar_url = profile["avatarUrl"]
    if not avatar_url:
        return await ctx.send(embed=no_profile_picture())

    await ctx.send(content=f"{avatar_url}")
