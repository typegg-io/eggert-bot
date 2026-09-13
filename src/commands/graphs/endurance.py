
from discord import File
from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, take_universe
from context import BotContext
from database.typegg.users import get_running_maximum_by_length
from graphs.endurance import UserEnduranceData, render
from utils.errors import NoRankedRaces
from utils.messages import universe_subtext
from utils.schemas import Profile

max_users = 5

info = CommandInfo(
    name="endurance",
    aliases=["end"],
    description="Displays peak WPM achieved at each quote length.\n"
                "Shows your ability to maintain speed across longer quotes.\n"
                f"Supports up to {max_users} users.",
    parameters=f"[username1] ... [username{max_users}]",
    examples=[
        "-end",
        "-end eiko",
        "-end eiko me",
    ],
    author=231721357484752896,
)


class Endurance(Command):
    """Graph peak WPM achieved at each quote length."""

    supported_flags = {"raw", "language"}

    @commands.command(aliases=info.aliases)
    async def endurance(self, ctx: BotContext, *args: str):
        """Graph the endurance curve for each user named."""
        await take_universe(ctx)
        profiles = await self.get_profiles(ctx, args, max_users)
        await run(ctx, profiles)


async def run(ctx: BotContext, profiles: list[Profile]) -> None:
    """Send a graph of each user's running maximum WPM by quote length."""
    data = []

    for profile in profiles:
        bests = get_running_maximum_by_length(profile["userId"], ctx.flags.language.name, ctx.flags.raw)
        if not bests:
            raise NoRankedRaces(profile["username"])

        wpm_values, length_values = map(list, zip(*((r["wpm"], r["length"]) for r in bests)))

        data.append(UserEnduranceData(profile["username"], wpm_values, length_values))

    file_name = render(
        profile["username"] if profile["userId"] == ctx.user["userId"] else "",
        data,
        ctx.user["theme"],
        ctx.flags.raw,
    )

    file = File(file_name, filename=file_name)

    await ctx.send(content=universe_subtext(ctx) or None, file=file)
