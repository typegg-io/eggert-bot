from typing import List

from discord import File
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.users import get_running_maximum_by_length
from graphs.endurance import UserEnduranceData, render

max_users = 5

info = {
    "name": "endurance",
    "aliases": ["end"],
    "description": "Displays peak WPM achieved at each quote length.\n"
                   "Shows your ability to maintain speed across longer quotes.\n"
                   f"Supports up to {max_users} users.",
    "parameters": f"[username1] ... [username{max_users}]",
    "examples": [
        "-end",
        "-end eiko",
        "-end eiko me",
    ],
    "author": 231721357484752896,
}


class Endurance(Command):
    @commands.command(aliases=info["aliases"])
    async def endurance(self, ctx: BotContext, *args: str):
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles)


async def run(ctx: BotContext, profiles: List[dict]):
    data = []

    for profile in profiles:
        bests = get_running_maximum_by_length(profile["userId"])
        wpm_values, length_values = map(list, zip(*((r["wpm"], r["length"]) for r in bests)))

        data.append(UserEnduranceData(profile["username"], wpm_values, length_values))

    file_name = render(
        profile["username"] if profile["userId"] == ctx.user["userId"] else "",
        data,
        ctx.user["theme"]
    )

    file = File(file_name, filename=file_name)

    await ctx.send(file=file)
