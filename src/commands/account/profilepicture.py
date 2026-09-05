
from discord import Embed
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from utils.colors import ERROR
from utils.schemas import Profile

info = CommandInfo(
    name="profilepicture",
    aliases=["avatar", "pfp"],
    description="Displays a user's TypeGG profile picture.",
    parameters="[username]",
    examples=[
        "-pfp",
        "-pfp eiko",
    ],
)


class ProfilePicture(Command):
    """Display a user's TypeGG profile picture."""

    ignore_flags = True

    @commands.command(aliases=info.aliases)
    async def profilepicture(self, ctx: BotContext, username: str | None = None):
        """Resolve the username without requiring races, then post their avatar."""
        profile = await self.get_profile(ctx, username, races_required=False)
        await run(ctx, profile)


def no_profile_picture() -> Embed:
    """Return the embed shown when a user has no avatar set."""
    return Embed(
        title="No Profile Picture",
        description="User does not have a profile picture",
        color=ERROR,
    )


async def run(ctx: BotContext, profile: Profile) -> None:
    """Post the profile's avatar URL, or an error when it has none."""
    avatar_url = profile["avatarUrl"]
    if not avatar_url:
        return await ctx.send(embed=no_profile_picture())

    await ctx.send(content=f"{avatar_url}")
