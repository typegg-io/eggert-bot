from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.races import get_quote_race_counts
from graphs.keystrokes import render
from utils.data_structures import ScaledCounter
from utils.keyboard_layouts import get_keymap
from utils.messages import Page, Message, Field

keyboard_layouts = ["qwerty", "dvorak"]
info = {
    "name": "keystrokes",
    "aliases": ["ks"],
    "description": "Displays a keystroke heatmap across all of a user's races.\n"
                   "Based on quote text, so corrections are not included.\n"
                   "Shift keys represent total capitalizations.\n"
                   "Supported layouts: " + ", ".join([f"`{kl}`" for kl in keyboard_layouts]),
    "parameters": "[username] [keyboard_layout]",
    "examples": [
        "-ks",
        "-ks eiko",
        "-ks skypromp dvorak",
    ],
    "author": 231721357484752896,
}


class Keystrokes(Command):
    @commands.command(aliases=info["aliases"])
    async def keystrokes(self, ctx: BotContext, *args: str):
        args, username, keyboard_layout = self.extract_params(args, keyboard_layouts)
        profile = await self.get_profile(ctx, username)

        if keyboard_layout is None:
            keyboard_layout = profile["hardware"]["layout"] or "qwerty"

        await run(ctx, profile, keyboard_layout.lower())


async def run(ctx: BotContext, profile: dict, keyboard_layout: str):
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
