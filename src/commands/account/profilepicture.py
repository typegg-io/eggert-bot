from typing import Optional

from discord import Embed
from discord.ext import commands

from commands.base import Command
from utils.colors import ERROR

info = {
    "name": "profilepicture",
    "aliases": ["avatar", "pfp"],
    "description": "Displays a user's TypeGG profile picture",
    "parameters": "[username]",
}


class ProfilePicture(Command):
    @commands.command(aliases=info["aliases"])
    async def profilepicture(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username)
        await run(ctx, profile)


def no_profile_picture():
    return Embed(
        title="No Profile Picture",
        description="User does not have a profile picture",
        color=ERROR,
    )


async def run(ctx: commands.Context, profile: dict):
    avatar_url = profile["avatarUrl"]
    if not avatar_url:
        return await ctx.send(embed=no_profile_picture())

    await ctx.send(content=f"{avatar_url}")
