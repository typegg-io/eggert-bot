from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.races import get_quote_race_counts
from graphs.keystrokes import render
from utils.data_structures import ScaledCounter
from utils.keyboard_layouts import get_keymap
from utils.messages import Page, Message, Field

info = {
    "name": "keystrokes",
    "aliases": ["ks"],
    "description": (
        "Shows a keystroke heatmap across all of a user's races.\n"
        "Based on quote data, not race data (corrections not included).\n\n"
        "Shift keys represent total capitalizations.\n"
        "Supported layouts: QWERTY, DVORAK\n"
        "Non-standard characters are excluded."
    ),
    "parameters": "[username] [keyboard_layout]",
    "author": 231721357484752896,
}


class Keystrokes(Command):
    @commands.command(aliases=info["aliases"])
    async def keystrokes(self, ctx, username: str = "me", keyboard_layout: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        if keyboard_layout is None:
            keyboard_layout = profile["hardware"]["layout"] or "qwerty"

        await run(ctx, profile, keyboard_layout.lower())


async def run(ctx: commands.Context, profile: dict, keyboard_layout: str):
    username = profile["username"]
    keymap, keyboard_layout = get_keymap(keyboard_layout)
    keypresses = get_keypresses(profile["userId"])

    description = (
        f"**Keyboard Layout:** {keyboard_layout.upper()}\n\n"
        f"**Most Frequent Characters**\n"
    )
    fields = []

    batch_size = 10
    top_keypresses = sorted(keypresses.items(), key=lambda item: -item[1])[:3 * batch_size]

    for i in range(0, len(top_keypresses), batch_size):
        batch = top_keypresses[i:i + batch_size]
        content = "\n".join(
            f"`{REPLACEMENT_CHARACTERS.get(char, char)}` ➜ {count:,}"
            for char, count in batch
        )
        fields.append(Field(title="", content=content, inline=True))

    page = Page(
        title="Keystrokes",
        description=description,
        fields=fields,
        render=lambda: render(
            username,
            keyboard_layout,
            keypresses,
            keymap,
            ctx.user["theme"],
        )
    )

    message = Message(ctx, page=page, profile=profile)

    await message.send()


REPLACEMENT_CHARACTERS = {
    "`": "´",
    "\n": "⏎",
}


def get_keypresses(user_id: str) -> ScaledCounter:
    keypresses = ScaledCounter()
    quote_frequencies = get_quote_race_counts(user_id)

    for text, race_count in quote_frequencies:
        keypresses += ScaledCounter(text) * race_count

    return keypresses
