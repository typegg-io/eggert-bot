from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command
from commands.summary.marathon import WindowData, drop_durations, get_window_data, take_duration
from commands.summary.races import build_stat_fields
from context import BotContext
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import format_duration
from utils.windows import Window, race_span, session_windows

CATEGORIES = ["races", "time"]
DEFAULT_BREAK = 1800

info = CommandInfo(
    name="session",
    aliases=["ss"],
    description="Displays a user's biggest sessions, a session being races no further apart than a given break.\n"
                "Break can be given as a duration (`1h30m`) or a number of seconds.",
    parameters="[username] <category:races|time> <break:30m>",
    examples=[
        "-session",
        "-session time",
        "-session eiko time 1h",
    ],
)


class Session(Command):
    """Display a user's biggest sessions for a given break between races."""

    supported_flags = {"gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def session(self, ctx: BotContext, *args: str):
        """Read the break and the category, then find the biggest sessions."""
        break_seconds = take_duration(ctx, DEFAULT_BREAK)
        params = self.extract_params(drop_durations(args), extract=CATEGORIES)
        profile = await self.get_profile(ctx, params.username)

        await run(ctx, profile, params.argument or "races", break_seconds)


def window_line(data: WindowData, window: Window, category: str) -> str:
    """Return one line describing a session's size and which races it covers."""
    start, end, _ = window
    races = end - start
    span = format_duration(data.ends[end - 1] - data.starts[start], show_seconds=False)
    numbers = race_span(data.races[start], data.races[end - 1])

    if category == "time":
        return f"**{span}** over {races:,} races {numbers}"

    return f"**{races:,}** races in {span} {numbers}"


async def run(ctx: BotContext, profile: Profile, category: str, break_seconds: float) -> None:
    """Send the 10 biggest sessions, by race count or by the time they spanned."""
    data = await get_window_data(ctx, profile, False)

    windows = session_windows(data.starts, data.ends, break_seconds, category == "time")
    windows.sort(key=lambda window: -window[2])
    # Sessions never overlap, so the top 10 needs no disjoint pass.
    top_windows = windows[:10]

    best = top_windows[0]
    break_title = format_duration(break_seconds)
    title = "Longest Session" if category == "time" else "Biggest Session"

    pages = [Page(
        title=f"{title} ({break_title} break)",
        description=window_line(data, best, category),
        fields=build_stat_fields(profile, data.races[best[0]:best[1]], ctx.flags),
        button_name="Best",
        flag_title=True,
    )]

    top_10 = ""

    for i, window in enumerate(top_windows, start=1):
        top_10 += f"{i}. {window_line(data, window, category)}\n"

    pages.append(Page(
        title=f"Top 10 {title}s ({break_title} break)",
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
