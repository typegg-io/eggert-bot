from discord.ext import commands

from command_info import CommandInfo
from commands.base import Command, default_to_quickplay
from context import BotContext
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.dates import discord_date, parse_date
from utils.errors import NotEnoughRaces, NumberGreaterThan
from utils.flags import is_multiplayer
from utils.messages import Message, Page
from utils.schemas import Profile
from utils.strings import date_range_display, pp_display

info = CommandInfo(
    name="bestaverages",
    aliases=["ba"],
    description="Displays a user's top 10 best averages of n consecutive races.\n"
                "Averages are non-overlapping.\n"
                "Use `pp` or `acc` to rank by pp or accuracy instead of WPM.",
    parameters="[username] [n:25] [wpm|pp|acc]",
    examples=[
        "-ba",
        "-ba eiko",
        "-ba eiko 50",
        "-ba eiko 50 pp",
        "-ba eiko 50 acc",
    ],
    privacy=True,
)


class BestAverages(Command):
    """Display a user's 10 best averages over n consecutive races."""

    supported_flags = {"metric", "raw", "gamemode", "status", "language", "number", "date_range"}

    @commands.command(aliases=info.aliases)
    async def bestaverages(self, ctx: BotContext, *args: str):
        """Default to 25 quickplay races, then rank the best non-overlapping windows."""
        await default_to_quickplay(ctx)
        n = int(abs(ctx.flags.number)) if ctx.flags.number is not None else 25
        params = self.extract_params(args, ["accuracy"])
        # Flags.metric defaults to pp, so only a typed metric counts here.
        metric = params.argument or (ctx.flags.metric if "metric" in ctx.explicit_flags else "wpm")
        self.check_raw_pp(ctx, metric == "pp")

        profile = await self.get_profile(ctx, params.username)
        await run(ctx, profile, n, metric)


async def run(ctx: BotContext, profile: Profile, n: int, metric: str = "wpm") -> None:
    """Send the 10 best non-overlapping windows of n races, by speed, pp or accuracy."""
    if n < 1:
        raise NumberGreaterThan

    race_list = await get_races(
        user_id=profile["userId"],
        columns=["wpm", "raceNumber", "timestamp", "accuracy", "pp", "quoteId"],
        flags=ctx.flags,
    )

    if n > len(race_list):
        raise NotEnoughRaces

    # All averages (sliding window)
    metric_values = [race[metric] or 0 for race in race_list]
    averages = []

    for i in range(len(race_list) - n + 1):
        window = metric_values[i:i + n]
        average = sum(window) / n
        averages.append((average, i))

    sorted_averages = sorted(averages, key=lambda x: x[0], reverse=True)

    # Find top 10 best non-overlapping averages
    best_averages = []
    used_indices = set()

    for average, start_index in sorted_averages:
        window_indices = set(range(start_index, start_index + n))
        if not window_indices & used_indices:
            best_averages.append((average, start_index))
            used_indices.update(window_indices)

            if len(best_averages) >= 10:
                break

    best_averages.sort(key=lambda x: x[0], reverse=True)

    quote_list = get_quotes()
    hide_raw_pp = ctx.flags.raw and not ctx.user["isGgPlus"]
    show_pp = ctx.flags.status == "ranked"

    top_average_desc = ""
    description = ""

    for rank, (average, start_index) in enumerate(best_averages, 1):
        start_race = race_list[start_index]
        end_race = race_list[start_index + n - 1]

        start_number = start_race["raceNumber"]
        end_number = end_race["raceNumber"]
        start_date = start_race["timestamp"]
        end_date = end_race["timestamp"]

        window_stats = format_window(race_list[start_index:start_index + n], quote_list, show_pp, hide_raw_pp)
        date_range = date_range_display(parse_date(start_date), parse_date(end_date), ctx.user["timezone"], short=True)
        description += (
            f"**{date_range}** (Races {f"#{start_number:,}" if start_number else "DNF"} - "
            f"{f"#{end_number:,}" if end_number else "DNF"})\n"
            f"{window_stats}\n\n"
        )

        if not top_average_desc:
            top_average_desc += description

    metric_label = {"wpm": "WPM", "pp": "pp", "accuracy": "Accuracy"}[metric]
    pages = [Page(
        title=f"Best Last {n:,} {metric_label} Averages",
        description=description if description else "No averages found",
        button_name="Best Averages",
        flag_title=True,
    )]

    if best_averages and (
        ctx.user["userId"] == profile["userId"]
        or is_multiplayer(ctx.flags)
    ):
        top_average, top_start_index = best_averages[0]

        start_offset = max(0, n - 25)  # If n > 25, start from the last 25 races

        top_races = race_list[top_start_index + start_offset:top_start_index + n]

        race_descriptions = ""
        for race in top_races:
            if race["wpm"] == 0:
                desc = "DNF - "
            else:
                desc = (
                    f"{race["wpm"]:,.2f} WPM - "
                    f"{race["accuracy"]:.2%} - " +
                    (f"{pp_display(race["pp"], hide_raw_pp)} - " if race["pp"] > 0 else "")
                )

            desc += (
                f"{quote_list[race["quoteId"]]["difficulty"]:.2f}★ - "
                f"{discord_date(race["timestamp"])} - "
                f"[<:quote_link:1483237184482836540>](https://typegg.io/solo/{race["quoteId"]})\n"
            )

            race_descriptions += desc

        if n > 25:
            race_descriptions += f"+{n - 25:,} others"

        pages.append(Page(
            title=f"Top {metric_label} Average of {n:,}",
            description=f"{top_average_desc}**Races:**\n" + race_descriptions,
            button_name="Top Average",
            flag_title=True,
        ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()


def format_window(window: list, quote_list: dict, show_pp: bool, hide_raw_pp: bool) -> str:
    """Return a window's average WPM, accuracy, pp and difficulty, counting a DNF as zero."""
    n = len(window)
    wpm = sum(race["wpm"] or 0 for race in window) / n
    accuracy = sum(race["accuracy"] or 0 for race in window) / n
    difficulty = sum(quote_list[race["quoteId"]]["difficulty"] for race in window) / n

    parts = [f"{wpm:,.2f} WPM", f"{accuracy:.2%}"]
    if show_pp:
        pp = sum(race["pp"] or 0 for race in window) / n
        parts.append(pp_display(pp, hide_raw_pp))
    parts.append(f"{difficulty:.2f}★")

    return " - ".join(parts)
