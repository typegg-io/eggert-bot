from typing import List

from discord import File
from discord.ext import commands

from commands.base import Command
from database.typegg.users import get_running_maximum_by_length
from graphs.endurance import UserEnduranceData, render

max_users_shown = 5

info = {
    "name": "endurance",
    "aliases": ["end"],
    "description": "Displays peak WPM achieved up until each quote length,\n"
                   "showing user's abilities to maintain their typing speed.\n"
                   f"Can be generated for up to {max_users_shown} users.",
    "parameters": f"[username1] [username2] ... [username{max_users_shown}]",
    "author": 231721357484752896,
}


class Endurance(Command):
    @commands.command(aliases=info["aliases"])
    async def endurance(self, ctx, *other_users: str):
        other_users = list(dict.fromkeys(other_users))  # Deduplicate & maintain order
        usernames = other_users[:max_users_shown] or [ctx.user["userId"]]
        profiles = []

        for username in usernames:
            profile = await self.get_profile(ctx, username, races_required=True)
            profiles.append(profile)
            await self.import_user(ctx, profile)

        await run(ctx, profiles)


async def run(ctx: commands.Context, profiles: List[dict]):
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
