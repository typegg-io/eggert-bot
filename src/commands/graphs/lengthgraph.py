from discord import File
from discord.ext import commands

from bot_setup import BotContext
from commands.base import Command
from database.typegg.users import get_best_by_length
from graphs import lengthgraph as lengthgraph_renderer
from graphs.lengthgraph import UserLengthData

max_users = 5

info = {
    "name": "lengthgraph",
    "aliases": ["leng"],
    "description": "Displays peak pp (or WPM) at each quote length.\n"
                   "Shows how your performance varies across short and long quotes.\n"
                   f"Supports up to {max_users} users.",
    "parameters": f"[username1] ... [username{max_users}]",
    "examples": [
        "-leng",
        "-leng eiko",
        "-leng eiko me",
        "-leng eiko -wpm",
    ],
}


class LengthGraph(Command):
    supported_flags = {"metric"}

    @commands.command(aliases=info["aliases"])
    async def lengthgraph(self, ctx: BotContext, *args: str):
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles)


async def run(ctx: BotContext, profiles: list):
    metric = ctx.flags.metric
    data = []

    for profile in profiles:
        rows = get_best_by_length(profile["userId"], metric)
        if not rows:
            continue
        values, lengths = zip(*((r["value"], r["length"]) for r in rows))
        data.append(UserLengthData(profile["username"], list(values), list(lengths)))

    first_username = profiles[0]["username"] if profiles[0]["userId"] == ctx.user["userId"] else ""

    file_name = lengthgraph_renderer.render(
        first_username,
        data,
        metric,
        ctx.user["theme"],
    )

    file = File(file_name, filename=file_name)
    await ctx.send(file=file)
