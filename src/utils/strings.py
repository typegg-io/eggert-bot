from typing import Optional

from dateutil import parser
from dateutil.relativedelta import relativedelta

from config import SITE_URL
from utils.errors import InvalidArgument, InvalidNumber
from utils.urls import race_url, profile_url

# Constants

RANK_EMOJIS = [
    ":first_place:",
    ":second_place:",
    ":third_place:",
    "<:4th:1219161348253159444>",
    "<:5th:1219161347082944563>",
    "<:6th:1219163724531892224>",
    "<:7th:1219163723650826260>",
    "<:8th:1219163721704931370>",
    "<:9th:1219163722455453707>",
    "<:10th:1219163725223694336>",
    "<:11th:1292341426557943878>",
    "<:12th:1384880520592097472>",
    "<:13th:1384880519065505912>",
    "<:14th:1384880518033702983>",
    "<:15th:1384880516989194260>",
    "<:16th:1384880515395616788>",
    "<:17th:1384880513785004104>",
    "<:18th:1384880512279117934>",
    "<:19th:1384880510723162153>",
    "<:20th:1384880508999041178>",
]

LOADING = "<a:loading:1418688762745065594>"
INCREASE = "<:increase:1372466536693891142>"
GG_PLUS = "<:GG1:1445664315871985807><:GG2:1445664341742452798>"
EGGERT = "<:eggertHappy:1327614782446108725>"
GG_PLUS_LINK = f"{SITE_URL}/plus"

OPTION_ALIASES = {
    "accuracy": ["acc", "ac"],
    "errorReactionTime": ["reaction", "react"],
    "errorRecoveryTime": ["recovery", "recover"],
    "characters": ["chars"],
    "quickplay": ["qp", "multiplayer", "multi", "mp"],
    "unranked": ["ur"],
    "playtime": ["pt"],
    "submissions": ["qs"],
}

ALIAS_LOOKUP = {
    alias.lower(): original
    for original, aliases in OPTION_ALIASES.items()
    for alias in [original, *aliases]
}

LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "tr": "Turkish",
    "no": "Norwegian",
    "id": "Indonesian",
    "la": "Latin",
}


# Argument & Parameter Parsing

def get_argument(valid_options: list[str], param: str, _raise: bool = True):
    """Resolve a parameter to its original option using aliases, or raise InvalidArgument."""
    param = param.lower()
    if param in valid_options:
        return param

    original = ALIAS_LOOKUP.get(param)
    if original not in valid_options:
        if _raise:
            raise InvalidArgument(valid_options)
        else:
            return None

    return original


def get_key_by_alias(alias_dict, alias):
    """Find the original key in an alias dictionary by checking all aliases."""
    for name, aliases in alias_dict.items():
        if alias in [name] + aliases:
            return name
    return None


def get_flag_title(flags):
    """Build a parenthetical title string from command flags (e.g., '(Raw, Solo)')."""
    flag_titles = []
    if flags.get("metric"):
        flag_titles.append("Raw")
    if flags.get("gamemode"):
        flag_titles.append(flags["gamemode"].title())
    if flags.get("status"):
        flag_titles.append(flags["status"].title())
    if flags.get("language"):
        flag_titles.append(LANGUAGES.get(flags["language"]))

    if not flag_titles:
        return ""

    return " (" + ", ".join(flag_titles) + ")"


# Number Formatting

def ordinal_number(number):
    """Convert a number to its ordinal string representation (e.g., 1st, 2nd, 3rd)."""
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if number % 100 in [11, 12, 13]:
        suffix = "th"
    return f"{number:,}{suffix}"


def format_big_number(number, _):
    """Format large numbers with K/M suffixes (e.g., 1500 -> 1.5K, 2000000 -> 2M)."""
    if number >= 1_000_000:
        return f"{round(number / 1_000_000, 1)}M".replace(".0", "")
    elif number >= 1_000:
        return f"{round(number / 1_000, 1)}K".replace(".0", "")
    return int(number)


def parse_number(value):
    """Parse a string into int or float, supporting commas and K/M suffixes."""
    s = str(value).strip().replace(",", "").lower()

    if s.endswith("k"):
        return round(float(s[:-1]) * 1_000)
    if s.endswith("m"):
        return round(float(s[:-1]) * 1_000_000)

    for caster in (int, float):
        try:
            return caster(s)
        except ValueError:
            continue

    raise InvalidNumber


def rank(number):
    """Return a rank emoji for numbers 1-20, or bold number for others."""
    if 1 <= number <= 20:
        return RANK_EMOJIS[number - 1]
    return f"**{number}**"


# Date & Time Formatting

def format_duration(seconds, round_seconds=True):
    """Format seconds into human-readable duration (e.g., '2d 3h 15m 42s')."""
    if round_seconds:
        seconds = round(seconds)
    if seconds == 0:
        return "0s"

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    days = f"{d:,.0f}d " * (d != 0)
    hours = f"{h:,.0f}h " * (h != 0)
    minutes = f"{m:,.0f}m " * (m != 0)
    seconds = f"{round(s, 0 if round_seconds else 3)}s " * (s != 0)

    return f"{days}{hours}{minutes}{seconds}"[:-1]


def discord_date(date_string: str, style: Optional[str] = "R"):
    """Convert a date string or timestamp to Discord's date format tag."""
    try:
        timestamp = int(date_string)
    except ValueError:
        timestamp = int(parser.parse(date_string).timestamp())
    return f"<t:{timestamp}:{style}>"


def date_range_display(start, end):
    """Format a date range into a readable string, omitting redundant year/month info."""
    from utils.dates import format_date

    end -= relativedelta(microseconds=1)

    start_year, end_year = start.year, end.year
    start_month, end_month = start.strftime("%B"), end.strftime("%B")
    start_day, end_day = ordinal_number(start.day), ordinal_number(end.day)

    if start_year == end_year and start_month == end_month and start_day == end_day:
        return format_date(start)

    display_string = (
        f"{start_month} {start_day}, {start_year} - "
        f"{end_month} {end_day}, {end_year}"
    )

    if start_year == end_year:
        display_string = display_string.replace(f", {start_year}", "", 1)

        if start_month == end_month:
            temp_month = f"{start_month} "[::-1]
            temp_string = display_string[::-1]
            temp_string = temp_string.replace(temp_month, "", 1)
            display_string = temp_string[::-1]

    return display_string


# Text Formatting

def escape_formatting(string, remove_backticks=True):
    """Escape Discord markdown formatting characters in a string."""
    backtick_sub = "" if remove_backticks else "\\`"
    return (
        string
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("~", "\\~")
        .replace("||", "\\|\\|")
        .replace("`", backtick_sub)
        .replace("-", "\\-")
    )


def truncate_clean(text: str, max_chars: int, max_lines: int):
    """Truncate text to max chars/lines, avoiding mid-word cuts and escaping formatting."""
    lines = text.splitlines()
    if len(lines) > max_lines:
        text = "\n".join(lines[:max_lines])
        text = text.rstrip() + "..."

    if len(text) <= max_chars:
        return escape_formatting(text, remove_backticks=False)

    if " " not in text:
        return escape_formatting(text[:max_chars] + "...", remove_backticks=False)

    substring = text[:max_chars]
    while len(substring) > 1 and substring[-1].isalnum():
        substring = substring[:-1]
    substring = substring.rstrip() + "..."

    return escape_formatting(substring, remove_backticks=False)


# User & Quote Displays

def get_flag(user):
    """Return a country flag emoji if user has a country, otherwise empty string."""
    country = user.get("country", None)
    return f":flag_{country.lower()}: " if country else ""


def username_with_flag(profile: dict, link_user: bool = True):
    """Format username with country flag and optional GG+ badge, optionally linked."""
    flag = get_flag(profile)
    username = profile["username"]
    gg_plus_display = GG_PLUS if profile.get("isGgPlus") else ""

    if link_user:
        display_name = username
        if username.find("_") != username.rfind("_"):
            display_name = username.replace("_", "ˍ")
        return f"{flag}[{display_name}]({profile_url(username)}) {gg_plus_display}"
    else:
        return f"{flag}{escape_formatting(username)} {gg_plus_display}"


def quote_display(
    quote: dict,
    max_text_chars: int = 60,
    max_text_lines: int = 15,
    display_author: bool = False,
    display_status: bool = False,
    display_racers_users: bool = False,
    display_submitted_by: bool = False,
    display_text: bool = True,
):
    """Format a quote dictionary into a rich display string for Discord embeds."""
    text = quote["text"]
    display_string = f"**[{quote["source"]["title"]}]({race_url(quote["quoteId"])})**"

    if display_author:
        display_string += f" by **{quote["source"]["author"]}**\n"
    else:
        display_string += " | "

    display_string += f"{quote["difficulty"]:.2f}★ | {len(text):,}c"

    if display_status:
        display_string += f" | {"Ranked" if quote["ranked"] else "Unranked"}"

    if display_racers_users:
        display_string += f" | {quote["races"]:,} races | {quote["uniqueUsers"]:,} users"

    display_string += "\n"

    if display_submitted_by:
        submitted_by = quote["submittedByUsername"]
        display_string += (
            f"**Submitted by:** [{submitted_by}]({profile_url(submitted_by)}) - "
            f"{discord_date(quote["created"], "D")}\n\n"
        )

    if display_text:
        display_string += f"\"{truncate_clean(text, max_text_chars, max_text_lines)}\"\n"

    return display_string


def get_segments(text: str):
    """Split a string into 10 approximately equal segments, without slicing between words."""
    # Create initial segments
    num_segments = 10
    split_index = len(text) / num_segments
    segments = []
    start_index = 0
    end_index = int(split_index)

    for i in range(num_segments):
        segments.append([start_index, end_index])
        start_index = int(split_index * (i + 1))
        end_index = int(split_index * (i + 2))

    adjusted_segments = []
    text_segments = []

    for i in range(len(segments)):
        start, end = segments[i]

        # For all segments except the last
        if i < len(segments) - 1:
            # Find the nearest space forward from the current end position
            forward_space = text.find(' ', end)
            # Find the nearest space backward from the current end position
            backward_space = text.rfind(' ', 0, end)

            # If we found both spaces, choose the closest one
            if forward_space != -1 and backward_space != -1:
                # Calculate distances
                forward_dist = forward_space - end
                backward_dist = end - backward_space

                if forward_dist <= backward_dist:
                    new_end = forward_space
                else:
                    new_end = backward_space
            elif forward_space != -1:  # Only forward space found
                new_end = forward_space
            elif backward_space != -1:  # Only backward space found
                new_end = backward_space
            else:  # No spaces found
                new_end = end

            # Ensure segments don't overlap and maintain order
            if i > 0 and new_end <= adjusted_segments[i - 1][1]:
                # If new end overlaps with previous segment, find next space after previous segment
                new_end = text.find(' ', adjusted_segments[i - 1][1] + 1)
                if new_end == -1:  # If no space found, use the end of text
                    new_end = len(text)

            adjusted_segments.append([start, new_end])
            # Extract the text segment (end index is exclusive in slicing)
            text_segments.append(text[start:new_end + 1])

            # Set start of next segment to be after this segment's end
            if i < len(segments) - 1:
                segments[i + 1][0] = new_end + 1 if new_end + 1 < len(text) else new_end
        else:
            # Last segment - extend to end of text
            adjusted_segments.append([start, len(text)])
            text_segments.append(text[start:len(text)])

    while text_segments[-1] == "":
        text_segments.pop()

    return text_segments
