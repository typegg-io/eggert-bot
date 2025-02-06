from discord import Embed, Forbidden
from discord.ext import commands

from api.verification import generate_link
from config import bot_prefix as prefix
from database.users import get_user
from utils.errors import red

info = {
    "name": "link",
    "aliases": ["verify"],
    "description": "Allows you to link your Discord and TypeGG accounts",
    "parameters": "",
}


async def setup(bot: commands.bot):
    await bot.add_cog(Link(bot))


class Link(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def link(self, ctx):
        author = ctx.author.id
        bot_user = get_user(author)

        if bot_user["user_id"]:
            return await ctx.send(embed=already_verified())

        link = generate_link(author)

        embed = Embed(
            title="Link Your TypeGG Account",
            description=f"To verify your account, click [**here**]({link}) and\n"
                        f"follow the instructions on the website.",
            color=bot_user["theme"]["embed"]
        )

        try:
            await ctx.author.send(embed=embed)
        except Forbidden:
            return await ctx.send(embed=dms_disabled())


def already_verified():
    return Embed(
        title="Already Verified",
        description="Your account is already linked.\n"
                    f"Run `{prefix}unlink` to unlink your account.",
        color=red,
    )


def dms_disabled():
    return Embed(
        title="Message Failed",
        description="Failed to send a direct message. Please enable\n"
                    "direct messages to receive the verification link.",
        color=red,
    )
