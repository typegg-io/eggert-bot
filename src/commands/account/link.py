from discord import Embed, Forbidden
from discord.ext import commands

from api.verification import generate_link
from bot_setup import BotContext
from commands.base import Command
from config import BOT_PREFIX, STAGING
from database.bot.users import link_user
from utils.colors import ERROR
from utils.messages import Message, Page

info = {
    "name": "link",
    "aliases": ["verify"],
    "description": "Links your Discord account to your TypeGG account.",
    "examples": ["-link"],
}


class Link(Command):
    ignore_flags = True

    @commands.command(aliases=info["aliases"])
    async def link(self, ctx: BotContext):
        if STAGING and ctx.raw_args:  # Skip verification process for development
            profile = await self.get_profile(ctx, ctx.raw_args[0])
            link_user(ctx.author.id, profile["userId"])
            message = Message(
                ctx, page=Page(
                    title="Account Linked",
                    description=f"Linked your account to `{profile["username"]}`"
                )
            )
            return await message.send()

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
