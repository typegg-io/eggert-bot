from typing import Optional

from discord.ext import commands

from api.users import get_race
from commands.base import Command
from database.typegg.quotes import get_quote
from database.typegg.users import get_quote_bests
from graphs import segments as segment_graph
from utils.errors import NoQuoteRaces
from utils.keystrokes import get_keystroke_data
from utils.messages import Page, Message, Field
from utils.stats import calculate_wpm
from utils.strings import escape_formatting, get_segments, discord_date, quote_display

info = {
    "name": "segments",
    "aliases": ["sg", "words", "wg"],
    "description": "Displays a bar graph of WPM segments over a race\n"
                   "Passing a quote ID will show the user's best race for that quote.",
    "parameters": "[username] [number/quote_id]",
}


class Segments(Command):
    @commands.command(aliases=info["aliases"])
    async def segments(self, ctx, username: Optional[str] = "me", race_identifier: Optional[str] = None):
        profile = await self.get_profile(ctx, username, races_required=True)
        await self.import_user(ctx, profile)

        try:
            race_number = await self.get_race_number(profile, race_identifier)
        except Exception:
            quote = await self.get_quote(ctx, race_identifier, profile["userId"])
            quote_bests = get_quote_bests(profile["userId"], quote_id=quote["quoteId"])
            if not quote_bests:
                raise NoQuoteRaces(profile["username"])
            race_number = quote_bests[0]["raceNumber"]

        await run(ctx, profile, race_number)


def format_segment(segment: dict, show_race: bool = False) -> str:
    """Format a segment with WPM and text, showing raw WPM as tooltip if higher."""
    text = segment["text"]
    if len(text) > 100:
        text = f"{text[:100]}..."

    wpm, raw_wpm = segment["wpm"], segment["raw_wpm"]
    race_num = segment.get("raceNumber")
    timestamp = segment.get("timestamp")

    # Build tooltip text
    if show_race and race_num:
        if timestamp:
            from dateutil import parser
            from utils.dates import format_date

            date = parser.parse(timestamp)
            formatted_date = format_date(date)
            tooltip = f"Race #{race_num:,}\n{formatted_date}"
        else:
            tooltip = f"Race #{race_num}"
        wpm_text = f"**[{wpm:,.2f}](http://a \"{tooltip}\")**"
    elif raw_wpm > wpm:
        wpm_text = f"**[{wpm:,.2f}](http://a \"{raw_wpm:,.2f} Raw\")**"
    else:
        wpm_text = f"**{wpm:,.2f}**"

    count = segment.get("count", 1)
    count_text = f" (x{count})" if count > 1 else ""

    return f"{wpm_text} - {escape_formatting(text)}{count_text}"


def build_segments(parts: list[str], delays: list, raw_delays: list) -> list[dict]:
    """Build segment WPM data from text parts and keystroke delays."""
    segments = []
    char_index = 0

    for text in parts:
        length = len(text)
        segment_delays = delays[char_index:char_index + length]
        raw_segment_delays = raw_delays[char_index:char_index + length]

        # Adjust for first segment if it starts at time 0
        adjustment = 1 if segment_delays[0] == 0 else 0
        char_count = len(segment_delays) - adjustment

        segments.append({
            "text": text,
            "wpm": calculate_wpm(sum(segment_delays), char_count),
            "raw_wpm": calculate_wpm(sum(raw_segment_delays), char_count),
            "delays": segment_delays,
        })
        char_index += length

    return segments


def build_word_segments(text: str, delays: list, raw_delays: list) -> tuple[list[dict], float, float]:
    """Build word WPM data excluding separators, and calculate average space/newline speeds."""
    words = []
    current_word = ""
    current_delays = []
    current_raw_delays = []
    space_delays = []
    newline_delays = []

    for i, char in enumerate(text):
        if char in " \n":
            if current_word:
                adjustment = 1 if current_delays[0] == 0 else 0
                char_count = len(current_delays) - adjustment
                words.append({
                    "text": current_word,
                    "wpm": calculate_wpm(sum(current_delays), char_count),
                    "raw_wpm": calculate_wpm(sum(current_raw_delays), char_count),
                })
                current_word = ""
                current_delays = []
                current_raw_delays = []

            if char == " ":
                space_delays.append(delays[i])
            else:
                newline_delays.append(delays[i])
        else:
            current_word += char
            current_delays.append(delays[i])
            current_raw_delays.append(raw_delays[i])

    if current_word:
        adjustment = 1 if current_delays[0] == 0 else 0
        char_count = len(current_delays) - adjustment
        words.append({
            "text": current_word,
            "wpm": calculate_wpm(sum(current_delays), char_count),
            "raw_wpm": calculate_wpm(sum(current_raw_delays), char_count),
        })

    space_speed = calculate_wpm(sum(space_delays), len(space_delays)) if space_delays else 0
    newline_speed = calculate_wpm(sum(newline_delays), len(newline_delays)) if newline_delays else 0

    return words, space_speed, newline_speed


async def run(ctx: commands.Context, profile: dict, race_number: int):
    race = await get_race(profile["userId"], race_number, get_keystrokes=True)
    quote = get_quote(race["quoteId"])
    keystroke_data = get_keystroke_data(race["keystrokeData"])
    delays = keystroke_data.wpmCharacterTimes
    raw_delays = keystroke_data.rawCharacterTimes

    segments = build_segments(get_segments(quote["text"]), delays, raw_delays)
    word_segments, avg_space_wpm, avg_newline_wpm = build_word_segments(quote["text"], delays, raw_delays)
    word_segments = [w for w in word_segments if w["wpm"] != float("inf")]

    # Average WPM for duplicate words
    word_totals = {}
    for word in word_segments:
        text = word["text"]
        if text not in word_totals:
            word_totals[text] = {"wpm": [], "raw_wpm": []}
        word_totals[text]["wpm"].append(word["wpm"])
        word_totals[text]["raw_wpm"].append(word["raw_wpm"])

    unique_words = [
        {
            "text": text,
            "wpm": sum(data["wpm"]) / len(data["wpm"]),
            "raw_wpm": sum(data["raw_wpm"]) / len(data["raw_wpm"]),
            "count": len(data["wpm"]),
        }
        for text, data in word_totals.items()
    ]

    fastest_words = sorted(unique_words, key=lambda x: -x["wpm"])
    slowest_words = sorted(unique_words, key=lambda x: x["wpm"])
    # Swap wpm/raw_wpm so format_segment displays raw as the main value
    slowest_raw = sorted(
        [{"text": w["text"], "wpm": w["raw_wpm"], "raw_wpm": w["wpm"], "count": w["count"]} for w in unique_words],
        key=lambda x: x["wpm"],
    )

    separator_stats = f"**Space Speed:** {avg_space_wpm:,.2f} WPM"
    if avg_newline_wpm:
        separator_stats += f"\n**Newline Speed:** {avg_newline_wpm:,.2f} WPM"

    description = (
        f"Completed {discord_date(race['timestamp'])}\n\n"
        f"{quote_display(quote, display_status=True, display_text=False)}\n"
        f"**Speed:** {race['wpm']:,.2f} WPM ({race['accuracy']:.2%} Accuracy)\n"
        f"**Raw Speed:** {race['rawWpm']:,.2f} WPM ({race['wpm'] / race['rawWpm']:.2%} Flow)\n"
        f"{separator_stats}\n\n"
    )
    segment_description = description + "**WPM - Segment**\n" + "\n".join(format_segment(s) for s in segments)

    segment_page = Page(
        title=f"WPM Segments - Race #{race_number:,}",
        description=segment_description,
        render=lambda: segment_graph.render(
            segments,
            title=f"WPM Segments - {profile["username"]} - Race #{race_number:,}",
            x_label="Segment",
            theme=ctx.user["theme"],
        ),
        button_name="Segments",
    )

    word_page = Page(
        title=f"Words - Race #{race_number:,}",
        description=description,
        fields=[
            Field(
                title="Fastest",
                content="\n".join(format_segment(word) for word in fastest_words[:10]),
                inline=True,
            ),
            Field(
                title="Slowest",
                content="\n".join(format_segment(word) for word in slowest_words[:10]),
                inline=True,
            ),
            Field(
                title="Slowest Raw",
                content="\n".join(format_segment(word) for word in slowest_raw[:10]),
                inline=True,
            )
        ],
        render=lambda: segment_graph.render(
            word_segments,
            title=f"Words - {profile["username"]} - Race #{race_number:,}",
            x_label="Word",
            theme=ctx.user["theme"],
        ),
        button_name="Words",
        default=ctx.invoked_with in ["words", "wg"],
    )

    message = Message(
        ctx,
        pages=[segment_page, word_page],
        profile=profile,
    )

    await message.send()
