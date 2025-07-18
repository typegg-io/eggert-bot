from typing import Optional

import matplotlib.colors as mcolors
from discord import Embed, File
from discord.ext import commands

from config import default_theme, dark_theme, light_theme
from database import users
from database.users import get_user
from graphs import sample
from graphs.core import remove_file
from utils import errors
from utils.errors import RED

elements = [
    "embed",
    "axis",
    "background",
    "graph_background",
    "grid",
    "line",
    "text",
]
info = {
    "name": "theme",
    "aliases": ["st"],
    "description": "Allows for customization of embed and graph colors",
    "parameters": "[element] [color]",
}


async def setup(bot: commands.Bot):
    await bot.add_cog(Theme(bot))


class Theme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def theme(self, ctx, element: str, color: Optional[str]):
        bot_user = get_user(ctx.author.id)

        themes = {
            "dark": dark_theme,
            "light": light_theme,
            "default": default_theme,
            "typegg": default_theme,
        }
        theme = themes.get(element, None)
        if theme:
            bot_user["theme"] = theme
            return await run(ctx, bot_user)

        elif element == "reset":
            bot_user["theme"] = default_theme
            return await run(ctx, bot_user)

        if element not in elements:
            return await ctx.send(embed=invalid_element())

        if not color:
            return await ctx.send(embed=errors.missing_arguments(info))

        if color == "off" and element == "grid":
            bot_user["theme"]["grid"] = None
            return await run(ctx, bot_user)

        parsed_color = parse_color(color)
        if not parsed_color:
            return await ctx.send(embed=invalid_color())

        if element != "embed":
            parsed_color = ("#%06x" % parsed_color)  # Converting integer to hex string (#FFFFFF)
        bot_user["theme"][element] = parsed_color

        await run(ctx, bot_user)


async def run(ctx: commands.Context, bot_user: dict):
    users.update_theme(str(ctx.author.id), bot_user["theme"])

    embed = Embed(
        title="Theme Updated",
        color=bot_user["theme"]["embed"],
    )

    file_name = f"sample_graph.png"
    sample.render(bot_user["theme"])

    embed.set_image(url=f"attachment://{file_name}")
    file = File(file_name, filename=file_name)

    await ctx.send(embed=embed, file=file)

    remove_file(file_name)


def parse_color(color):
    if type(color) == int:
        return color
    try:
        number = int(color, 16)
    except ValueError:
        try:
            hex_code = mcolors.to_hex(color)
            number = int(hex_code[1:], 16)
        except ValueError:
            return None

    if number < 0 or number > 0xFFFFFF:
        return None
    return number


def invalid_element():
    return Embed(
        title="Invalid Element",
        description="Element must be: " + ", ".join([f"`{element}`" for element in elements]),
        color=RED,
    )


def invalid_color():
    return Embed(
        title="Invalid Color",
        description="Color must be a valid hex code",
        color=RED,
    )
