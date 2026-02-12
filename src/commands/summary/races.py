from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta
from discord.ext import commands

from commands.base import Command
from database.typegg.quotes import get_quotes
from database.typegg.races import get_races
from database.typegg.users import get_quote_bests
from utils.dates import count_unique_dates, parse_date, get_start_end_dates
from utils.errors import NoRacesFiltered
from utils.messages import Page, Message, Field
from utils.stats import calculate_quote_length, calculate_duration, calculate_quote_bests, calculate_total_pp
from utils.strings import format_duration, discord_date, get_flag_title, date_range_display

info = {
    "name": "races",
    "aliases": ["rd"],
    "description": "Displays detailed race information about a user's account",
    "parameters": "[username]",
}


class Races(Command):
    @commands.command(aliases=info["aliases"])
    async def races(self, ctx, username: Optional[str] = "me"):
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        await run(ctx, profile)


def build_stat_fields(profile, race_list, flags, all_time=False):
    quote_list = get_quotes()
    multiplayer = flags.gamemode in ["quickplay", "lobby"]

    cumulative_values = {
        "wpm": [], "rawWpm": [], "accuracy": [], "duration": [],
        "errorReactionTime": [], "errorRecoveryTime": [],
    }

    total_races = 0
    solo_races = 0
    multiplayer_races = 0
    dnf_count = 0
    wins = 0
    best = {"pp": race_list[0], "wpm": race_list[0]}
    total_duration = 0
    correction_duration = 0
    words_typed = 0
    chars_typed = 0

    longest_break = {
        "start_race": next(
            (race for race in race_list if race["raceNumber"] is not None), None
        ),
        "duration": 0
    }

    if not longest_break["start_race"]:
        raise NoRacesFiltered(profile["username"])

    previous_race = None

    for race in race_list:
        completion_type = race["completionType"] if multiplayer else "finished"
        if completion_type != "finished":
            dnf_count += 1
            cumulative_values["wpm"].append(0)
            cumulative_values["rawWpm"].append(0)
            continue

        total_races += 1

        for key in cumulative_values:
            if "error" in key:
                cumulative_values[key].append(min(race[key], 2000))
            else:
                cumulative_values[key].append(race[key])

        quote_length = calculate_quote_length(race["wpm"], race["duration"])

        if race["rawWpm"] == 0:  # temporary catch for invalid raw speeds
            race = dict(race)
            race["rawWpm"] = race["wpm"]

        raw_duration = calculate_duration(race["rawWpm"], quote_length - 1)
        correction_duration += race["duration"] - raw_duration

        if race["matchId"] is None:
            solo_races += 1
        else:
            multiplayer_races += 1
            if multiplayer and race["placement"] == 1:
                wins += 1

        if race["pp"] > best["pp"]["pp"]:
            best["pp"] = race

        if race["wpm"] > best["wpm"]["wpm"]:
            best["wpm"] = race

        total_duration += race["duration"]

        quote = quote_list[race["quoteId"]]
        words = quote["text"].split()
        words_typed += len(words)
        chars_typed += quote_length

        if previous_race is not None:
            break_time = (
                parse_date(race["timestamp"]).timestamp() -
                parse_date(previous_race["timestamp"]).timestamp()
            )

            if break_time > longest_break["duration"]:
                longest_break.update({
                    "start_race": previous_race,
                    "duration": break_time,
                })

        previous_race = race

    for key in cumulative_values:
        if len(cumulative_values[key]) > 0:
            cumulative_values[key] = sum(cumulative_values[key]) / len(cumulative_values[key])
        else:
            cumulative_values[key] = 0

    total_duration /= 1000

    period_quote_bests = calculate_quote_bests(race_list)
    period_total_pp = calculate_total_pp(period_quote_bests)
    end_date = parse_date(race_list[-1]["timestamp"]) + relativedelta(microseconds=1000)

    quote_bests = get_quote_bests(
        user_id=profile["userId"],
        end_date=end_date,
        flags=flags,
    )
    total_pp = calculate_total_pp(quote_bests)

    min_timestamp = race_list[0]["timestamp"]
    old_quote_bests = get_quote_bests(
        user_id=profile["userId"],
        end_date=min_timestamp,
        flags=flags,
    )
    old_total_pp = calculate_total_pp(old_quote_bests)

    fields = [
        Field(
            title="Performance",
            content=(
                f"**Total:** {period_total_pp:,.0f} pp\n"
                f"**Effective Gain:** +{total_pp - old_total_pp:,.2f} pp\n"
                f"**Best Score:** {best["pp"]["pp"]:,} pp (Race #{best["pp"]["raceNumber"]:,})"
            )
        ),
        Field(
            title="Speed",
            content=(
                f"**Average Speed:** {cumulative_values["wpm"]:,.2f} WPM "
                f"({cumulative_values["accuracy"]:.2%} Accuracy)\n"
                f"**Raw Speed:** {cumulative_values["rawWpm"]:,.2f} WPM "
                f"({abs(correction_duration / (cumulative_values["duration"] * total_races)):.2%} Correction)\n"
                f"**Top Speed:** {best["wpm"]["wpm"]:,.2f} WPM (Race #{best["wpm"]["raceNumber"]:,})\n"
                f"**Error Reaction:** {cumulative_values["errorReactionTime"]:,.0f}ms / "
                f"**Error Recovery:** {cumulative_values["errorRecoveryTime"]:,.0f}ms"
            )
        )
    ]

    unique_quotes = len(period_quote_bests)
    new_quotes = len(quote_bests) - len(old_quote_bests)

    start_date = race_list[0]["timestamp"]
    end_date = race_list[-1]["timestamp"]
    start_time = parse_date(start_date).timestamp()
    end_time = parse_date(end_date).timestamp()
    timespan = end_time - start_time

    fields.append(Field(
        title="Activity",
        content=(
            f"**Races:** {total_races:,}" +
            (f" / **DNFs:** {dnf_count:,}\n" if multiplayer else "\n") +
            f"**Solo:** {solo_races:,} / **Quickplay:** {multiplayer_races :,}\n" +
            (f"**Wins:** {wins:,} ({wins / (multiplayer_races + dnf_count):.2%} win rate)\n" if wins > 0 else "") +
            f"**Quotes:** {unique_quotes:,}" +
            (f" ({new_quotes:,} new)\n" if new_quotes > 0 and not all_time else "\n") +
            f"**Quote Repeats:** {total_races / unique_quotes:,.2f}\n"
            f"**Words Typed:** {words_typed:,}\n"
            f"**Characters Typed:** {chars_typed:,}\n"
            f"**Completion Play Time:** {format_duration(total_duration)}\n"
            f"**Timespan:** {format_duration(timespan)} "
            f"({discord_date(start_time, "d")} - {discord_date(end_time, "d")})\n"
            f"**Longest Break:** {format_duration(longest_break["duration"])} "
            f"(Starting on #{longest_break["start_race"]["raceNumber"]:,})\n"
        )
    ))

    unique_days = count_unique_dates(start_date, end_date)
    if unique_days > 1:
        fields.append(Field(
            title=f"Daily Average (Over {unique_days:,} days)",
            content=(
                f"**Races:** {total_races / unique_days:.2f}\n"
                f"**Play Time:** {format_duration(total_duration / unique_days)}"
            )
        ))

    return fields


async def run(
    ctx: commands.Context,
    profile: dict,
    date: datetime = None,
    period: str = None,
):
    flags = ctx.flags
    flags.status = flags.status or "ranked"
    start_date, end_date = get_start_end_dates(date, period)

    race_list = await get_races(
        user_id=profile["userId"],
        start_date=start_date,
        end_date=end_date,
        flags=flags,
    )

    if race_list:
        fields = build_stat_fields(
            profile,
            race_list,
            flags,
            start_date is None and end_date is None,
        )
        description = ""
    else:
        fields = []
        description = "No races completed"

    title = "Race Stats"

    if flags.status in ["ranked", "unranked"]:
        title = f"{flags.status.title()} {title}"

    flags.status = None
    title += get_flag_title(flags)

    if start_date:
        title += "\n" + date_range_display(start_date, end_date)

    page = Page(
        title=title,
        fields=fields,
        description=description,
    )

    message = Message(
        ctx,
        page=page,
        profile=profile,
    )

    await message.send()
