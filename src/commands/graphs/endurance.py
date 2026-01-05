from typing import Optional, List
from discord import File
from discord.ext import commands
from database.typegg.users import get_running_maximum_by_length
from commands.base import Command
from graphs.endurance import UserEnduranceData, render


max_users_shown = 5
log_base = 10

info = {
    "name": "endurance",
    "aliases": ["end"],
    "description": "Displays a graph of a user's ranked WPM PB over the quote length.\n"
                   f"This graph can be generated for up to {max_users_shown} users.",
    "parameters": f"[username1] [username2] ... [username{max_users_shown}]",
    "author": 231721357484752896,
}


class Endurance(Command):
    @commands.command(aliases=info["aliases"])
    async def endurance(self, ctx, username: Optional[str] = "me", *other_users: str):
        other_users = other_users[:max_users_shown - 1]
        profile = await self.get_profile(ctx, username, races_required=True)

        usernames = set(other_users)
        usernames.add(username)
        profiles = [await self.get_profile(ctx, username, races_required=True) for username in usernames]

        for profile in profiles:
            await self.import_user(ctx, profile)

        await run(ctx, profiles)


async def run(ctx: commands.Context, profiles: List[dict]):
    data = []

    for profile in profiles:
        bests = get_running_maximum_by_length(profile["userId"], log=log_base)
        wpm_values, length_values = zip(*((race["wpm"], race["length"]) for race in bests))

        data.append(UserEnduranceData(profile["username"], wpm_values, length_values))

    file_name = render(
            profile["username"] if profile["userId"] == ctx.user["userId"] else "",
            data,
            log_base,
            ctx.user["theme"]
    )

    file = File(file_name, filename=file_name)

    await ctx.send(file=file)

