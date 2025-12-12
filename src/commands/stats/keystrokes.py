from typing import Optional, List
from discord.ext import commands
from commands.base import Command
from database.typegg.users import get_quote_bests
from utils.messages import Page, Message
from utils.strings import get_flag_title
from graphs.keystrokes import render
from utils.keyboard_layouts import getKeymap
from utils.scaled_counter import ScaledCounter


info = {
    "name": "keystrokes",
    "aliases": ["ks"],
    "description": "Displays the aggregation of all your keystrokes on typegg across all your quotes. Note that this uses the quotes data and not the replay data, so corrections will not be taken into account. This is for performance reasons.\n"
    "The following keyboard layouts are implemented, more can be added: ['qwerty', 'dvorak']\n"
    "Also note that both shifts will be represented as the total amount of shift presses, since there's no way to distinguish between them. Also Caps Lock has not been implemented yet, but might be reevaluated in the future.",
    "parameters": f"[username1] [keyboard_layout]",
    "author": 231721357484752896,
}


class Keystrokes(Command):
    @commands.command(aliases=info["aliases"])
    async def keystrokes(self, ctx, username: str = "me", keyboard_layout: Optional[str] = None):
        username = self.get_username(ctx, username)

        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        if keyboard_layout is None:
            keyboard_layout = profile["hardware"]["layout"]  # Can return None

            if keyboard_layout is None:
                keyboard_layout = "qwerty"

        await run(ctx, profile, keyboard_layout.lower())


async def run(ctx: commands.Context, profile: dict, keyboard_layout: str):
    username = profile["username"]
    keymap, keyboard_layout = getKeymap(keyboard_layout)

    if profile["userId"] == ctx.user["userId"]:
        username = profile["username"]

    # quotes = get_quote_bests(profile["userId"], columns=["quotes"], flags={"status": "ranked"})
    # quotes = list(map(lambda quote: (quote["quote"]["text"], quote["attepmts"]), quotes))
    quotes = [("hello how are you doing..............", 5), ("I like eiko :)", 3)]

    keypresses = ScaledCounter()

    for text, attempts in quotes:
        keypresses += ScaledCounter(text) * attempts

    description = (
        f"**Keyboard layout:** {keyboard_layout}\n"
        f"**Most frequently typed characters:**\n"
        + "\n".join(map(lambda item: f"{item[0]}: {item[1]}", sorted(list(keypresses.items()), key=lambda item: -item[1])[:5]))
    )

    page = Page(
        title="Keystrokes",
        description=description,
        render=lambda: render(
            username,
            keyboard_layout,
            keypresses,
            keymap,
        )
    )

    message = Message(
        ctx,
        page=page
    )

    await message.send()

