from discord.ext import commands

from commands.base import Command
from config import KEEGAN
from database.bot.users import get_admin_users
from utils.messages import Page, Message

info = {
    "name": "about",
    "aliases": ["info"],
    "description": "Displays information about the bot",
    "parameters": "",
}


class About(Command):
    @commands.command(aliases=info["aliases"])
    async def about(self, ctx):
        message = Message(ctx, Page(
            title="Eggert",
            description=(
                f""
                f"{self.bot.user.mention} is a typing statistics Discord bot. It is designed to enhance\n"
                f"the <:typegg_logo:1421559259929382923> TypeGG experience, providing detailed insights and features.\n\n"
                f"Developed by <@{KEEGAN}>, written in <:python_logo:1219588087383064647> Python.\n"
                f"For source code and contributing, visit the <:github:1421565431533273269> "
                f"[GitHub Repository](https://github.com/typegg-io/eggert-bot)\n\n"
                f"**Bot Admins**\n" + ",".join(f"<@{user["discordId"]}>" for user in get_admin_users())
            ),
        ))

        await message.send()
