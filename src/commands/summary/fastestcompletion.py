from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.marathon import WindowData, get_window_data, is_pp_category
from commands.summary.races import build_stat_fields
from context import BotContext
from utils.errors import BotError, NotEnoughRaces, NumberGreaterThan
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import format_duration
from utils.windows import Window, completion_windows, race_span, top_disjoint_windows

DEFAULT_RACES = 100

info = CommandInfo(
    name="fastestcompletion",
    aliases=["fc"],
    description="Displays the shortest time a user has taken to complete a number of races, "
                "or to gain an amount of pp.",
    parameters="[username] <number:100> <category:races|pp>",
    examples=[
        "-fastestcompletion",
        "-fc 1000",
        "-fc eiko 500 pp",
    ],
)


class FastestCompletion(Command):
    """Display the quickest stretches in which a user reached an amount."""

    supported_flags = {"metric", "gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def fastestcompletion(self, ctx: BotContext, *args: str):
        """Read the amount and the category, then find the quickest windows."""
        params = self.extract_params(args, extract=["races"])
        profile = await self.get_profile(ctx, params.username)

        await run(ctx, profile, "pp" if is_pp_category(ctx) else "races", ctx.flags.number)


def window_line(data: WindowData, window: Window) -> str:
    """Return one line describing how long a window took and which races it covers."""
    start, end, duration = window

    return (
        f"**{format_duration(duration)}** over {end - start:,} races "
        f"{race_span(data.races[start], data.races[end - 1])}"
    )


async def run(ctx: BotContext, profile: Profile, category: str, number: float | None) -> None:
    """Send the 10 quickest non-overlapping windows reaching a number of races or pp."""
    target = DEFAULT_RACES if number is None else abs(number)

    if category == "races":
        target = round(target)
        if target <= 1:
            raise NumberGreaterThan(1)
    elif target <= 0:
        raise NumberGreaterThan(0)

    data = await get_window_data(ctx, profile, category == "pp")

    if category == "races" and len(data.races) < target:
        raise NotEnoughRaces

    windows = completion_windows(data.starts, data.ends, target, data.before, data.after)

    if not windows:
        raise BotError(
            "Not Enough pp",
            "User has never gained this much pp",
        )

    windows.sort(key=lambda window: window[2])
    top_windows = top_disjoint_windows(windows)

    best = top_windows[0]
    amount = f"{target:,.0f} pp" if category == "pp" else f"{target:,} Races"

    pages = [Page(
        title=f"Fastest {amount}",
        description=window_line(data, best),
        fields=build_stat_fields(profile, data.races[best[0]:best[1]], ctx.flags),
        button_name="Fastest",
        flag_title=True,
    )]

    top_10 = ""

    for i, window in enumerate(top_windows, start=1):
        top_10 += f"{i}. {window_line(data, window)}\n"

    pages.append(Page(
        title=f"Top 10 Fastest {amount}",
        description=top_10,
        button_name="Top 10",
        flag_title=True,
    ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
