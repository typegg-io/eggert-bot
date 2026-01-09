from discord.ext import commands

from commands.base import Command
from commands.checks import is_bot_owner
from database.typegg.db import get_row_count
from utils.messages import Page, Message

info = {
    "name": "database",
    "aliases": ["db"],
    "description": "Display database table stats",
}


class Database(Command):
    @commands.command(aliases=info["aliases"])
    @is_bot_owner()
    async def database(self, ctx):
        race_rows = get_row_count("races")
        user_rows = get_row_count("users")
        quote_rows = get_row_count("quotes")
        source_rows = get_row_count("sources")

        page = Page(
            title="Database Stats",
            description=(
                f"**Races:** {race_rows:,}\n"
                f"**Users:** {user_rows:,}\n"
                f"**Quotes:** {quote_rows:,}\n"
                f"**Sources:** {source_rows:,}\n"
            ),
        )

        message = Message(ctx, page=page)

        await message.send()
