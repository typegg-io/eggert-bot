from typing import List

from discord.ext import commands

from commands.base import Command
from config import GENERAL_CHANNEL_ID
from utils.errors import GeneralException
from utils.keyboard_layouts import get_keymap, K, keymaps as external_keymaps
from utils.messages import Page, Message, usable_in

supported_layouts_string = "Supported layouts: `QWERTY` (default), `Dvorak`, `Colemak`, `Gallium`"

info = {
    "name": "translate",
    "aliases": ["tr"],
    "description": f"Translates text between keyboard layouts.\n{supported_layouts_string}",
    "parameters": "[from layout] <to layout> <text>",
    "author": 231721357484752896
}


class Translate(Command):
    @commands.command(aliases=info["aliases"])
    @usable_in(GENERAL_CHANNEL_ID)
    async def translate(self, ctx, layout_from: str, *, text: str):
        words = text.split(" ")
        if words[0].lower() in external_keymaps:
            layout_to = words[0].lower()
            text = " ".join(words[1:])
        else:
            layout_from, layout_to = "qwerty", layout_from.lower()

        if layout_to not in external_keymaps:
            raise GeneralException("Invalid Layout", supported_layouts_string)

        keymap_from, layout_from = get_keymap(layout_from)
        keymap_from = get_keylist(keymap_from)

        keymap_to, layout_to = get_keymap(layout_to)
        keymap_to = get_keylist(keymap_to)

        keymapping = {key_from: key_to for key_from, key_to in zip(keymap_from, keymap_to)}

        translation = ""
        character_in_case_not_found = "\uFFFD"

        for character in text:
            mapped_char = keymapping.get(character)
            translation += mapped_char if mapped_char else character_in_case_not_found

        page = Page(
            title="Layout Translation",
            description=(
                f"**{layout_from.title()}**\n"
                f"`{text}`\n\n"
                f"**{layout_to.title()}**\n"
                f"`{translation}`"
            ),
            color=ctx.user["theme"]["embed"],
        )

        message = Message(ctx, page=page)
        await message.send()


def get_keylist(keystrokes: List[List[K]]) -> List[str | None]:
    keylist = []

    for keyrow in keystrokes:
        for key in keyrow:
            characters = list(key.matches)
            characters = (characters + [None] * max(4 - len(characters), 0))[:4]

            for character in characters:
                keylist.append(character)

    return keylist
