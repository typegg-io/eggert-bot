from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from context import BotContext
from database.typegg.races import get_races
from graphs import personal_best
from utils.dates import discord_date, get_timestamp_list
from utils.errors import NoRacesFiltered
from utils.messages import Message, Page
from utils.schemas import Profile

MILESTONE_STEPS = {"pp": 25, "wpm": 10}
MILESTONE_LIMIT = 40
LABELS = {"pp": "pp", "wpm": "WPM"}

info = CommandInfo(
    name="personalbestgraph",
    aliases=["pbg", "milestones"],
    description="Displays a user's personal best progression across every race.\n"
                "Lists the race that broke each milestone, every 25 pp or 10 WPM.",
    parameters="[username]",
    examples=[
        "-pbg",
        "-pbg eiko",
        "-pbg eiko -wpm",
    ],
)


class PersonalBestGraph(Command):
    """Graph a user's personal best progression and list the milestones it broke."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "date_range"}

    @commands.command(aliases=info.aliases)
    async def personalbestgraph(self, ctx: BotContext, *args: str):
        """Resolve the profile from the arguments, then render it."""
        self.check_raw_pp(ctx, ctx.flags.metric == "pp")
        profile = await self.get_profile(ctx, args[0] if args else None)
        await run(ctx, profile)


def find_personal_bests(values: list[float]) -> list[int]:
    """Return the index of each value that beat every earlier one."""
    indices = []
    for i, value in enumerate(values):
        if not indices or value > values[indices[-1]]:
            indices.append(i)

    return indices


def find_milestones(values: list[float], best_indices: list[int], step: int) -> list[tuple[int, int]]:
    """Return each personal best that broke a multiple of step, paired with the highest one it broke."""
    milestones = []
    for previous, i in zip(best_indices, best_indices[1:]):
        barrier = int(values[i] // step * step)
        if barrier > values[previous]:
            milestones.append((i, barrier))

    return milestones


def build_milestone_lines(
    races: list[dict],
    metric: str,
    best_indices: list[int],
    milestones: list[tuple[int, int]],
) -> list[str]:
    """Return one line for the first race, each milestone, and the best race."""
    suffix = f" {LABELS[metric]}"
    entries = [("First Race", best_indices[0])]
    entries += [(f"Broke {barrier:,}{suffix}", i) for i, barrier in milestones]

    best = best_indices[-1]
    if entries[-1][1] == best:
        entries[-1] = (f"{entries[-1][0]} (Best)", best)
    else:
        entries.append(("Best", best))

    lines = []
    for title, i in entries:
        race = races[i]
        # Some match races were imported without a race number.
        number = f" - Race #{race["raceNumber"]:,}" if race["raceNumber"] is not None else ""
        lines.append(f"**{title}:** {race[metric]:,.2f}{suffix}{number} - {discord_date(race["timestamp"], "D")}")

    # Discord caps an embed description at 4,096 characters.
    if len(lines) > MILESTONE_LIMIT:
        hidden = len(lines) - MILESTONE_LIMIT
        lines = lines[:1] + [f"*{hidden:,} more milestones*"] + lines[-(MILESTONE_LIMIT - 1):]

    return lines


async def run(ctx: BotContext, profile: Profile) -> None:
    """Send a user's personal best progression with every milestone it broke."""
    metric = ctx.flags.metric
    race_list = await get_races(
        user_id=profile["userId"],
        columns=[metric, "raceNumber", "timestamp"],
        include_dnf=False,
        flags=ctx.flags,
    )

    if not race_list:
        raise NoRacesFiltered(profile["username"])

    values = [race[metric] for race in race_list]
    best_indices = find_personal_bests(values)
    milestones = find_milestones(values, best_indices, MILESTONE_STEPS[metric])
    lines = build_milestone_lines(race_list, metric, best_indices, milestones)

    header = (
        f"**Races:** {len(race_list):,}\n"
        f"**PB Improvements:** {len(best_indices) - 1:,}\n\n"
    ) + "\n".join(lines)

    label = LABELS[metric]
    milestone_indices = [i for i, _ in milestones]
    race_numbers = []
    for race in race_list:
        race_numbers.append(race["raceNumber"] or (race_numbers[-1] if race_numbers else 0))
    timestamps = get_timestamp_list([race["timestamp"] for race in race_list])

    def render(x: list[float], over_time: bool):
        """Return a renderer for the graph over the given x values."""
        return lambda: personal_best.render(
            x=x,
            values=values,
            best_indices=best_indices,
            milestone_indices=milestone_indices,
            metric=label,
            theme=ctx.user["theme"],
            over_time=over_time,
        )

    message = Message(
        ctx,
        title=f"{label} Milestones",
        header=header,
        pages=[
            Page(button_name="Over Races", render=render(race_numbers, False), flag_title=True),
            Page(button_name="Over Time", render=render(timestamps, True), flag_title=True),
        ],
        profile=profile,
    )

    await message.send()
