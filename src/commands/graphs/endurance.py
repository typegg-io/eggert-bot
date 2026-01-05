from typing import Optional
from discord import File
from discord.ext import commands
from database.typegg.users import get_running_maximum_by_length
from commands.base import Command
from graphs.endurance import render


metrics = {"difficulty": "difficulty", "diff": "difficulty", "length": "length", "len": "length", None: "length"}
info = {
    "name": "endurance",
    "aliases": ["end"],
    "description": "Displays a graph of a user's WPM pb over length or difficulty\n"
                   "\\- `metric` defaults to length",
    "parameters": "[username] [difficulty (diff)|length (len)]",
    "author": 231721357484752896,
}


class Endurance(Command):
    @commands.command(aliases=info["aliases"])
    async def endurance(self, ctx, username: Optional[str] = "me", metric: Optional[str] = None):
        if metric not in metrics:
            raise Exception("Metric not found")

        metric = metrics[metric]
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        await run(ctx, profile, metric)


async def run(ctx: commands.Context, profile: dict, metric: str):
    log = 10
    bests = get_running_maximum_by_length(profile["userId"], log=log)
    wpm_values = [race["wpm"] for race in bests]
    length_values = [race["length"] for race in bests]

    file_name = render(
            profile["username"],
            wpm_values,
            length_values,
            log,
            ctx.user["theme"],
    )

    file = File(file_name, filename=file_name)

    await ctx.send(file=file)
