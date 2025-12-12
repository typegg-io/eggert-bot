from typing import Optional
from api.users import get_quotes
from discord.ext import commands
from commands.base import Command
from utils.messages import Page, Message, Field
from graphs.keystrokes import render
from utils.keyboard_layouts import getKeymap
from utils.scaled_counter import ScaledCounter


info = {
    "name": "keystrokes",
    "aliases": ["ks"],
    "description": "Displays the aggregation of all your keystrokes on typegg across all your quotes. Note that this uses the quotes data and not the replay data, so corrections will not be taken into account. This is for performance reasons.\n"
    "The following keyboard layouts are implemented, more can be added: ['qwerty', 'dvorak']\n"
    "Also note that both shifts will be represented as the total amount of shift presses, since there's no way to distinguish between them. Also Caps Lock has not been implemented yet, but might be reevaluated in the future.\n"
    "Characters that are not on the default layouts will not be counted towards the total",
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

    keypresses = ScaledCounter()
    total_pages = 1
    page = 1
    max_iterations = 50

    while page <= total_pages or page > max_iterations:
        response = await get_quotes(user_id=profile["userId"], page=page, per_page=1000)
        total_pages = response["totalPages"]
        quotes = response["quotes"]
        quotes = list(map(lambda quote: (quote["quote"]["text"], quote["attempts"] if quote["attempts"] is not None else 1), quotes))  # Attempts can be None, probably because of old data

        for text, attempts in quotes:
            keypresses += ScaledCounter(text) * attempts

        page += 1

    description = (
        f"**Keyboard layout:** {keyboard_layout}\n"
        f"**Most frequently typed characters:**\n"
    )

    fields = []

    batch_size = 10
    sorted_keypresses = sorted(list(keypresses.items()), key=lambda item: -item[1])[:3 * batch_size]

    for i in range(0, len(sorted_keypresses), batch_size):
        mapped_frequencies = map(lambda item: f"{replaceCharacters(item[0])} **->** {item[1]}", sorted_keypresses[i:i + batch_size])
        stringified_frequencies = "\n".join(mapped_frequencies)
        fields.append(Field(
            title="",
            content=stringified_frequencies,
            inline=True,
        ))

    page = Page(
        title="Keystrokes",
        description=description,
        fields=fields,
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


replacement_characters = {"\n": "RET", " ": "SP", "-": "\-"}


def replaceCharacters(char: str):
    return char if char not in replacement_characters else replacement_characters[char]
