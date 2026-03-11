from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_admin
from config import KEEGAN
from database.typegg.quotes import reimport_quotes
from database.typegg.users import reimport_users
from utils.errors import MissingArguments, InvalidArgument
from utils.messages import Page, Message

categories = ["users", "quotes"]
info = {
    "name": "migrate",
    "aliases": [],
    "description": "Re-imports specified data for the bot's database",
    "parameters": "<category1> [category2] ...",
}


class Migrate(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_admin()
    async def migrate(self, ctx, *category_list: str):
        if not category_list:
            raise MissingArguments

        for category in category_list:
            if category not in categories:
                raise InvalidArgument(categories)

        message = Message(
            ctx, Page(title="Migration Started"),
        )
        await message.send()

        for category in category_list:
            match category:
                case "users":
                    await reimport_users()
                case "quotes":
                    await reimport_quotes()

        message = Message(
            ctx, Page(
                title="Migration Complete",
                description=(
                    "Completed migration for the categories:\n" +
                    ", ".join([f"`{category}`" for category in category_list])
                ),
            ),
            content=f"<@{KEEGAN}>",
        )
        await message.send()
