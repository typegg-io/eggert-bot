from typing import Optional

from discord import File
from discord.ext import commands

from api.users import get_top_quotes
from database.users import get_user
from graphs import best
from graphs.core import remove_file
from utils import errors

info = {
    "name": "best",
    "aliases": ["b"],
    "description": "Displays a graph of a user's top N pp quotes\n\\- `quote_count` defaults to 50",
    "parameters": "[username] <quote_count>",
}


async def setup(bot: commands.bot):
    await bot.add_cog(Best(bot))


class Best(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def best(self, ctx, username: Optional[str] = "me", quote_count: Optional[int] = 50):
        bot_user = get_user(ctx.author.id)

        if username == "me":
            username = bot_user["user_id"]
        if not username:
            return await ctx.send(embed=errors.missing_parameter(info))

        try:
            quote_count = int(quote_count)
        except ValueError:
            return await ctx.send(embed=errors.invalid_number())

        await run(ctx, bot_user, username, quote_count)


async def run(ctx: commands.Context, bot_user: dict, username: str, quote_count: Optional[int] = 50):
    top_quotes = await get_top_quotes(username, quote_count)

    title = f"Top {quote_count} PP Quotes"

    file_name = f"top_{quote_count}_quotes_{username}.png"
    title += f" - {username}"
    best.render(file_name, bot_user["theme"], top_quotes, title)

    file = File(file_name, filename=file_name)

    await ctx.send(file=file)

    remove_file(file_name)
