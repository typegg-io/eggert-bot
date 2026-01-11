from typing import List
from discord.ext import commands
from commands.base import Command
from utils.keyboard_layouts import get_keymap, K, keymaps as external_keymaps
from utils.messages import Page, Message


info = {
    "name": "translate",
    "aliases": ["tr"],
    "description": "Translate a text from one keyboard layout to another. Current supported layouts are `QWERTY`, `Dvorak`, `Colemak`, `Gallium`. Capitalisation of the layouts does not matter. The default `translates from` layout is QWERTY",
    "parameters": "[translates from layout] <translates to layout> <text to be translated>",
    "author": 231721357484752896
}


class Translate(Command):
    @commands.command(aliases=info["aliases"])
    async def translate(self, ctx, layout_from: str, *text_tuple: str):
        if text_tuple[0] in external_keymaps:
            layout_to = text_tuple[0]
            text_tuple = text_tuple[1:]
        else:
            layout_from, layout_to = "qwerty", layout_from

        text = " ".join(text_tuple)

        keymap_from, layout_from = get_keymap(layout_from.lower())
        keymap_from = get_keylist(keymap_from)

        keymap_to, layout_to = get_keymap(layout_to.lower())
        keymap_to = get_keylist(keymap_to)

        keymapping = {key_from: key_to for key_from, key_to in zip(keymap_from, keymap_to)}

        translation = ""
        character_in_case_not_found = "\uFFFD"

        for character in text:
            if character in keymapping:
                translated_character = keymapping[character]

                if translated_character is None or translated_character == "":
                    translated_character = character_in_case_not_found

            else:
                translated_character = character_in_case_not_found

            translation += translated_character

        page = Page(
            title=f"Translates from **{layout_from}** to **{layout_to}**",
            description=(translation),
        )

        message = Message(
            ctx,
            page=page,
        )

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
