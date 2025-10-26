from discord import Embed, Forbidden
from discord.ext import commands

from api.verification import generate_link
from commands.base import Command
from config import BOT_PREFIX
from utils.colors import ERROR

info = {
    "name": "link",
    "aliases": ["verify"],
    "description": "Allows you to link your Discord and TypeGG accounts",
}


class Link(Command):
    @commands.command(aliases=info["aliases"])
    async def link(self, ctx: commands.Context):
        if ctx.user["userId"]:
            return await ctx.send(embed=already_verified())

        link = generate_link(str(ctx.author.id))
        embed = Embed(
            title="Link Your TypeGG Account",
            description=f"To verify your account, click [**here**]({link}) and\n"
                        f"follow the instructions on the website.",
            color=ctx.user["theme"]["embed"]
        )

        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            return await ctx.send(embed=dms_disabled())


def already_verified():
    return Embed(
        title="Already Verified",
        description="Your account is already linked.\n"
                    f"Run `{BOT_PREFIX}unlink` to unlink your account.",
        color=ERROR,
    )


def dms_disabled():
    return Embed(
        title="Message Failed",
        description="Failed to send a direct message. Please enable\n"
                    "direct messages to receive the verification link.",
        color=ERROR,
    )
