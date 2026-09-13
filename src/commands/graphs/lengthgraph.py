from discord import File
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, take_universe
from context import BotContext
from database.typegg.users import get_best_by_length
from graphs import length
from utils.messages import universe_subtext

max_users = 5

info = CommandInfo(
    name="lengthgraph",
    aliases=["leng"],
    description="Displays peak pp (or WPM) at each quote length.\n"
                "Shows how your performance varies across short and long quotes.\n"
                f"Supports up to {max_users} users.",
    parameters=f"[username1] ... [username{max_users}]",
    examples=[
        "-leng",
        "-leng eiko",
        "-leng eiko me",
        "-leng eiko -wpm",
    ],
)


class LengthGraph(Command):
    """Graph peak pp or WPM at each quote length."""

    supported_flags = {"metric", "raw", "language"}

    @commands.command(aliases=info.aliases)
    async def lengthgraph(self, ctx: BotContext, *args: str):
        """Graph the length curve for each user named."""
        self.check_raw_pp(ctx, ctx.flags.metric == "pp")
        await take_universe(ctx)
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles)


async def run(ctx: BotContext, profiles: list) -> None:
    """Send a graph of each user's best score at every quote length."""
    metric = ctx.flags.metric
    data = []
    username = profiles[0]["username"]

    for profile in profiles:
        rows = get_best_by_length(profile["userId"], ctx.flags.language.name, metric, ctx.flags.raw)
        if not rows:
            continue
        values, lengths = zip(*((r["value"], r["length"]) for r in rows))
        data.append(length.UserLengthData(profile["username"], list(values), list(lengths)))

        if profile["userId"] == ctx.user["userId"]:
            username = profile["username"]

    file_name = length.render(
        username,
        data,
        metric,
        ctx.user["theme"],
        ctx.flags.raw,
    )

    file = File(file_name, filename=file_name)
    await ctx.send(content=universe_subtext(ctx) or None, file=file)
