from typing import Optional

from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from utils.dates import parse_date
from utils.errors import NumberGreaterThan, NotEnoughRaces
from utils.messages import Page, Message
from utils.strings import get_flag_title, date_range_display, parse_number, discord_date

info = {
    "name": "bestaverages",
    "aliases": ["ba"],
    "description": "Displays a user's top 10 best averages of n consecutive races (non-overlapping)",
    "parameters": "[username] [n]",
    "defaults": {
        "n": "25",
    },
}


class BestAverages(Command):
    @commands.command(aliases=info["aliases"])
    async def bestaverages(self, ctx, username: Optional[str] = "me", n: Optional[str] = "25"):
        n = parse_number(n)
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        await run(ctx, profile, n)


async def run(ctx: commands.Context, profile: dict, n: int):
    if n < 1:
        raise NumberGreaterThan

    ctx.flags.gamemode = ctx.flags.gamemode or "quickplay"
    flag_title = get_flag_title(ctx.flags)
    ctx.flags.status = ctx.flags.status or "ranked"

    race_list = await get_races(
        user_id=profile["userId"],
        columns=["wpm", "raceNumber", "timestamp", "accuracy", "pp", "quoteId"],
        flags=ctx.flags,
    )

    if n > len(race_list):
        raise NotEnoughRaces

    # All averages (sliding window)
    wpm_values = [race["wpm"] for race in race_list]
    averages = []

    for i in range(len(race_list) - n + 1):
        window = wpm_values[i:i + n]
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

    top_average_desc = ""
    description = ""

    for rank, (average, start_index) in enumerate(best_averages, 1):
        start_race = race_list[start_index]
        end_race = race_list[start_index + n - 1]

        start_number = start_race["raceNumber"]
        end_number = end_race["raceNumber"]
        start_date = start_race["timestamp"]
        end_date = end_race["timestamp"]

        description += (
            f"**{date_range_display(parse_date(start_date), parse_date(end_date))}**\n"
            f"{average:,.2f} WPM (Races {f"#{start_number:,}" if start_number else "DNF"} - "
            f"{f"#{end_number:,}" if end_number else "DNF"})\n\n"
        )

        if not top_average_desc:
            top_average_desc += description

    pages = [Page(
        title=f"Best Last {n:,} Averages" + flag_title,
        description=description if description else "No averages found",
        button_name="Best Averages",
    )]

    if best_averages and ctx.flags.gamemode in ["quickplay", "lobby"]:
        top_average, top_start_index = best_averages[0]

        start_offset = max(0, n - 25)  # If n > 25, start from the last 25 races

        top_races = race_list[top_start_index + start_offset:top_start_index + n]
        quote_list = get_quotes()

        race_descriptions = ""
        for race in top_races:
            if race["wpm"] == 0:
                desc = "DNF - "
            else:
                desc = (
                    f"{race["wpm"]:,.2f} WPM - "
                    f"{race["accuracy"]:.2%} - " +
                    (f"{race["pp"]:,.2f} pp - " if race["pp"] > 0 else "")
                )

            desc += (
                f"{quote_list[race["quoteId"]]["difficulty"]:.2f}★ - "
                f"{discord_date(race["timestamp"])} - "
                f"[<:quote:1470361772132143277>](https://typegg.io/solo/{race["quoteId"]})\n"
            )

            race_descriptions += desc

        if n > 25:
            race_descriptions += f"+{n - 25:,} others"

        pages.append(Page(
            title=f"Top Average of {n:,}" + flag_title,
            description=f"{top_average_desc}**Races:**\n" + race_descriptions,
            button_name="Top Average"
        ))

    message = Message(
        ctx,
        pages=pages,
        profile=profile,
    )

    await message.send()
