import re
from typing import Optional

import matplotlib.colors as mcolors
from discord import Embed
from discord.ext import commands

from commands.base import Command
from config import DEFAULT_THEME, DARK_THEME, LIGHT_THEME, KEEGAN
from database.bot.users import update_theme
from graphs import sample
from graphs.core import plt
from utils import strings
from utils.errors import ERROR, missing_arguments
from utils.messages import Page, Message

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
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "typegg": DEFAULT_THEME,
    "default": DEFAULT_THEME,
    "reset": DEFAULT_THEME,
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


class Theme(Command):
    @commands.command(aliases=info["aliases"])
    async def theme(self, ctx, element: str, color: Optional[str]):
        theme = themes.get(element, None)
        if theme:
            ctx.user["theme"] = theme
            return await run(ctx)

        element = strings.get_key_by_alias(elements, element)
        if element not in elements:
            return await ctx.send(embed=invalid_element())

        if not color:
            return await ctx.send(embed=missing_arguments(info))

        if element == "grid" and color == "off":
            ctx.user["theme"]["grid_opacity"] = 0
            return await run(ctx)

        elif element == "grid_opacity":
            try:
                alpha = float(color)
                if alpha < 0 or alpha > 1:
                    raise ValueError
            except ValueError:
                return await ctx.send(embed=invalid_opacity())
            ctx.user["theme"]["grid_opacity"] = alpha
            return await run(ctx)

        parsed_color = parse_color(color)
        if parsed_color is None:
            if element == "line" and color in plt.colormaps:
                if color == "keegan" and ctx.author.id != KEEGAN:
                    return await ctx.send(embed=colormap_reserved())
                ctx.user["theme"]["line"] = color
                return await run(ctx)
            else:
                return await ctx.send(embed=invalid_color())

        if element != "embed":
            parsed_color = ("#%06x" % parsed_color)  # Integer to hex string
        ctx.user["theme"][element] = parsed_color

        await run(ctx)


async def run(ctx: commands.Context):
    update_theme(str(ctx.author.id), ctx.user["theme"])

    page = Page(
        title="Theme Updated",
        color=ctx.user["theme"]["embed"],
        render=lambda: sample.render(ctx.user["theme"]),
    )

    message = Message(
        ctx,
        page=page,
    )

    await message.send()


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
        color=ERROR,
    )


def invalid_color():
    return Embed(
        title="Invalid Color",
        description="Color must be a valid hex code",
        color=ERROR,
    )


def invalid_opacity():
    return Embed(
        title="Invalid Opacity",
        description="Opacity must be a value between 0 and 1",
        color=ERROR,
    )


def colormap_reserved():
    return Embed(
        title="Colormap Reserved",
        description="This colormap is reserved",
        color=ERROR,
    )
