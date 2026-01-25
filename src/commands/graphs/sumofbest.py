import copy
from typing import Optional

from dateutil import parser
from discord.ext import commands

from commands.base import Command
from commands.graphs.segments import build_segments, format_segment
from database.typegg.races import get_races
from graphs import match as match_graph
from graphs import segments as segment_graph
from utils.errors import NoQuoteRaces
from utils.keystrokes import get_keystroke_data, calculate_wpm, get_keystroke_wpm
from utils.messages import Page, Message
from utils.strings import format_duration
from utils.strings import get_segments, quote_display

info = {
    "name": "sumofbest",
    "aliases": ["sob"],
    "description": "Displays your Sum of Best WPM segments merged to a single graph",
    "parameters": "[quote_id] [username]",
}


class SumOfBest(Command):
    @commands.command(aliases=info["aliases"])
    async def sumofbest(self, ctx, quote_id: Optional[str], username: Optional[str] = "me"):
        self.check_gg_plus(ctx)
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)
        quote = await self.get_quote(ctx, quote_id, user_id=profile["userId"])

        await run(ctx, profile, quote)


async def run(ctx: commands.Context, profile: dict, quote: dict):
    quote_races = await get_races(profile["userId"], quote_id=quote["quoteId"], order_by="rawWpm", get_keystrokes=True)
    if not quote_races:
        raise NoQuoteRaces(profile["username"])

    pp_ratio = quote_races[0]["pp"] / quote_races[0]["wpm"]
    text_segments = get_segments(quote["text"])
    sum_of_best_segments = []

    for race in quote_races:
        keystroke_data = get_keystroke_data(race["keystrokeData"])

        segments = build_segments(
            text_segments,
            keystroke_data.wpmCharacterTimes,
            keystroke_data.rawCharacterTimes,
        )

        if not sum_of_best_segments:
            sum_of_best_segments = copy.deepcopy(segments)
            for segment in sum_of_best_segments:
                segment["raceNumber"] = race.get("raceNumber")
                segment["timestamp"] = race.get("timestamp")
            continue

        for i, segment in enumerate(segments):
            if segment["wpm"] > sum_of_best_segments[i]["wpm"] and segment["text"] == text_segments[i]:
                sum_of_best_segments[i] = copy.deepcopy(segment)
                sum_of_best_segments[i]["raceNumber"] = race.get("raceNumber")
                sum_of_best_segments[i]["timestamp"] = race.get("timestamp")

    delays = [delay for segment in sum_of_best_segments for delay in segment["delays"]]
    sum_of_best_wpm = calculate_wpm(len(quote["text"]) - 1, sum(delays))
    sum_of_best_pp = sum_of_best_wpm * pp_ratio
    sum_of_best_keystroke_wpm = get_keystroke_wpm(delays)

    unique_races = set()
    timestamps = []
    for segment in sum_of_best_segments:
        race_num = segment.get("raceNumber")
        timestamp = segment.get("timestamp")
        if race_num:
            unique_races.add(race_num)
        if timestamp:
            timestamps.append(parser.parse(timestamp))

    unique_race_count = len(unique_races)
    if len(timestamps) > 1:
        time_span = (max(timestamps) - min(timestamps)).total_seconds()
        time_span_display = format_duration(time_span)
    else:
        time_span_display = "0s"

    stats_description = (
        f"**Score:** {sum_of_best_pp:,.2f} pp\n"
        f"**Speed:** {sum_of_best_wpm:,.2f} WPM\n"
        f"**Unique Races:** {unique_race_count:,}\n"
        f"**Timespan:** {time_span_display}\n"
    )

    segments_description = (
        f"{quote_display(quote, display_status=True, display_text=False)}\n"
        f"{stats_description}\n"
        "**WPM - Segment**\n"
    )
    segments_description += "\n".join(format_segment(s, show_race=True) for s in sum_of_best_segments)

    race_graph_description = (
        f"{quote_display(quote, display_status=True)}\n"
        f"{stats_description}"
    )

    segment_page = Page(
        title=f"WPM Segments (Sum of Best)",
        description=segments_description,
        render=lambda: segment_graph.render(
            sum_of_best_segments,
            title=f"WPM Segments - {profile["username"]} (Sum of Best)",
            x_label="Words",
            theme=ctx.user["theme"],
        ),
        button_name="Segments",
    )

    race_page = Page(
        title="Race Graph (Sum of Best)",
        description=race_graph_description,
        render=lambda: match_graph.render(
            race_data=[{
                "username": profile["username"],
                "keystroke_wpm": sum_of_best_keystroke_wpm,
            }],
            title=f"Race Graph - {profile["username"]} (Sum of Best)",
            theme=ctx.user["theme"],
        ),
        button_name="Race Graph"
    )

    message = Message(
        ctx,
        pages=[segment_page, race_page],
        profile=profile,
    )

    await message.send()
