import re
from typing import Optional

import matplotlib.colors as mcolors
from discord import Embed, File
from discord.ext import commands

from config import default_theme, dark_theme, light_theme
from database import users
from database.users import get_user
from graphs import sample
from graphs.core import plt, remove_file
from utils import errors, strings
from utils.errors import RED

# Name + aliases
elements = {
    "embed": ["em"],
    "axis": ["ax"],
    "background": ["bg"],
    "graph_background": ["graph", "gbg"],
    "grid": ["#"],
    "grid_opacity": ["go"],
    "line": ["-"],
    "title": [],
    "text": [],
}
themes = {
    "dark": dark_theme,
    "light": light_theme,
    "typegg": default_theme,
    "default": default_theme,
    "reset": default_theme,
}
info = {
    "name": "theme",
    "aliases": ["st"],
    "description": "Allows for customization of embed and graph colors\n"
                   "Pre-made themes:\n"
                   "`-theme typegg` (default)\n"
                   "`-theme dark`\n"
                   "`-theme light`",
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

        theme = themes.get(element, None)
        if theme:
            bot_user["theme"] = theme
            return await run(ctx, bot_user)

        element = strings.get_key_by_alias(elements, element)
        if element not in elements:
            return await ctx.send(embed=invalid_element())

        if not color:
            return await ctx.send(embed=errors.missing_arguments(info))

        if element == "grid" and color == "off":
            bot_user["theme"]["grid_opacity"] = 0
            return await run(ctx, bot_user)

        elif element == "grid_opacity":
            try:
                alpha = float(color)
                if alpha < 0 or alpha > 1:
                    raise ValueError
            except ValueError:
                return await ctx.send(embed=invalid_opacity())
            bot_user["theme"]["grid_opacity"] = alpha
            return await run(ctx, bot_user)

        parsed_color = parse_color(color)
        if parsed_color is None:
            if element == "line" and color in plt.colormaps:
                bot_user["theme"]["line"] = color
                return await run(ctx, bot_user)
            else:
                return await ctx.send(embed=invalid_color())

        if element != "embed":
            parsed_color = ("#%06x" % parsed_color)  # Integer to hex string
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


def parse_color(string):
    color = None
    try:
        hex_string = mcolors.to_hex(mcolors.to_rgb(string))
        color = int(hex_string[1:], 16)
    except ValueError:
        if bool(re.fullmatch(r"[0-9a-fA-F]+", string)):
            if len(string) == 2:
                string = string * 3
            color = parse_color("#" + string)

    return color


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


def invalid_opacity():
    return Embed(
        title="Invalid Opacity",
        description="Opacity must be a value between 0 and 1",
        color=RED,
    )
