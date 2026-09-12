from collections import Counter

from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.races import get_races
from utils.errors import NoRacesFiltered
from utils.messages import Field, Message, Page
from utils.schemas import Profile

info = CommandInfo(
    name="positionstats",
    aliases=["ps"],
    description="Displays where a user places in multiplayer races.",
    parameters="[username]",
    examples=[
        "-positionstats",
        "-ps eiko",
        "-ps eiko quickplay",
    ],
)


class PositionStats(Command):
    """Display where a user places in multiplayer races."""

    supported_flags = {"gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def positionstats(self, ctx: BotContext, *args: str):
        """Cover every multiplayer mode unless one was asked for, then render the placements."""
        ctx.flags.gamemode = ctx.flags.gamemode or "multiplayer"
        profile = await self.get_profile(ctx, args[0] if args else None)

        await run(ctx, profile)


def position_line(label: str, race: dict) -> str:
    """Return one placement highlight with the race it happened on."""
    return f"**{label}:** {race["placement"]}/{race["players"]:,} (Race #{race["raceNumber"]:,})\n"


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's win rate, their placement highlights and every position they have taken."""
    race_list = await get_races(
        user_id=profile["userId"],
        columns=["raceNumber", "placement", "players"],
        flags=ctx.flags,
    )
    if not race_list:
        raise NoRacesFiltered(profile["username"])

    positions = Counter()
    wins = 0
    most_racers = race_list[0]
    biggest_win = None
    biggest_loss = None
    longest_streak = (0, None, None)
    streak = 0
    streak_start = None

    for race in race_list:
        placement = race["placement"]
        players = race["players"]
        positions[(placement, players)] += 1

        if players > most_racers["players"]:
            most_racers = race

        # Winning a race nobody else entered is not a win.
        if placement == 1 and players > 1:
            wins += 1
            if biggest_win is None or players > biggest_win["players"]:
                biggest_win = race
            if streak == 0:
                streak_start = race
            streak += 1
            if streak > longest_streak[0]:
                longest_streak = (streak, streak_start, race)
        else:
            streak = 0

        if placement > 1 and (biggest_loss is None or placement > biggest_loss["placement"]):
            biggest_loss = race

    total = len(race_list)
    description = (
        f"**Races:** {total:,}\n"
        f"**Wins:** {wins:,} ({wins / total:.2%})\n"
        f"{position_line("Most Racers", most_racers)}"
    )

    if biggest_win is not None:
        description += position_line("Biggest Win", biggest_win)

    if biggest_loss is not None:
        description += position_line("Biggest Loss", biggest_loss)

    if longest_streak[0]:
        count, first, last = longest_streak
        span = (
            f"Race #{first["raceNumber"]:,}" if count == 1 else
            f"Races #{first["raceNumber"]:,} - #{last["raceNumber"]:,}"
        )
        description += f"**Longest Win Streak:** {count:,} ({span})\n"

    ranking = positions.most_common(30)
    fields = [
        Field(
            title="Positions" if start == 0 else "",
            content="\n".join(
                f"**{placement}/{players:,}:** {count:,}"
                for (placement, players), count in ranking[start:start + 10]
            ),
            inline=True,
        )
        for start in range(0, len(ranking), 10)
    ]

    page = Page(
        title="Position Stats",
        description=description,
        fields=fields,
        flag_title=True,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
