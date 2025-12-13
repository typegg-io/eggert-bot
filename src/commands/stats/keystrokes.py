from typing import Optional
from api.users import get_quotes
from discord.ext import commands
from commands.base import Command
from database.typegg.races import get_quotes_playcount
from utils.messages import Page, Message, Field
from graphs.keystrokes import render
from utils.keyboard_layouts import getKeymap
from utils.scaled_counter import ScaledCounter


info = {
    "name": "keystrokes",
    "aliases": ["ks"],
    "description": "Displays the aggregation of all your keystrokes on TypeGG across all your attempts. This uses the quote data, not the race data, so no corrections are being detected. (this is for performance reasons)\n\n"
    f"The following keyboard layouts are implemented: 'qwerty', 'dvorak'.\n\n"
    "Both shifts will be represented as the total amount of capitalisations.\n\n"
    "Characters that are not on the default layouts will not be counted towards the total.",
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

    keypresses = await getKeypressesApi(profile["userId"])
    # keypresses = getKeypressesDb(profile["userId"])

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


replacement_characters = {"\n": "RET", " ": "SP", "-": "\\-"}


def replaceCharacters(char: str):
    return char if char not in replacement_characters else replacement_characters[char]


def getKeypressesDb(userId: str):
    keypresses = ScaledCounter()

    race_frequencies = get_quotes_playcount(userId)

    for text, races in race_frequencies:
        keypresses += ScaledCounter(text) * races

    return keypresses


async def getKeypressesApi(userId: str):
    keypresses = ScaledCounter()
    total_pages = 1
    page = 1
    max_iterations = 50

    # TODO: Use get_quote_bests from the database instead of the API, currently the total attempts are not stored in the database and cannot be inferred
    while page <= total_pages or page > max_iterations:
        response = await get_quotes(user_id=userId, page=page, per_page=1000)
        total_pages = response["totalPages"]
        quotes = response["quotes"]
        quotes = map(lambda quote: (quote["quote"]["text"], quote["races"]), quotes)

        for text, races in quotes:
            keypresses += ScaledCounter(text) * races

        page += 1

    return keypresses
