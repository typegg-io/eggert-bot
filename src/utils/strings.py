from typing import Optional

from dateutil import parser

from utils.errors import InvalidArgument, InvalidNumber
from utils.urls import race_url, profile_url

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

OPTION_ALIASES = {
    "pp": ["performance", "pf"],
    "accuracy": ["acc", "ac"],
    "errorReactionTime": ["reaction", "react"],
    "errorRecoveryTime": ["recovery", "recover"],
    "characters": ["chars"],
}

ALIAS_LOOKUP = {
    alias.lower(): original
    for original, aliases in OPTION_ALIASES.items()
    for alias in [original, *aliases]
}


def get_argument(valid_options: list[str], param: str, _raise: bool = True):
    """Resolve a parameter to its original option if valid, else raise or None."""
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


def discord_date(date_string: str, style: Optional[str] = "R"):
    try:
        timestamp = int(date_string)
    except ValueError:
        timestamp = int(parser.parse(date_string).timestamp())
    return f"<t:{timestamp}:{style}>"


def get_key_by_alias(alias_dict, alias):
    for name, aliases in alias_dict.items():
        if alias in [name] + aliases:
            return name

    return None


# Formats seconds into: XXd XXh XXm XXs
def format_duration(seconds, round_seconds=True):
    if round_seconds:
        seconds = round(seconds)
    if seconds == 0: return "0s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    days = f"{d:,.0f}d " * (d != 0)
    hours = f"{h:,.0f}h " * (h != 0)
    minutes = f"{m:,.0f}m " * (m != 0)
    seconds = f"{round(s, 0 if round_seconds else 3)}s " * (s != 0)

    return f"{days}{hours}{minutes}{seconds}"[:-1]


def escape_formatting(string, remove_backticks=True):
    backtick_sub = "" if remove_backticks else "\\`"
    return (
        string
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("~", "\\~")
        .replace("||", "\\|\\|")
        .replace("`", backtick_sub)
    )


def truncate_clean(text: str, max_chars: int, max_lines: int):
    """Truncates a string to a maximum number of characters or lines, avoiding mid-word cuts."""
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


def ordinal_number(number):
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if number % 100 in [11, 12, 13]:
        suffix = "th"

    return f"{number:,}{suffix}"


def rank(number):
    if 1 <= number <= 20:
        return RANK_EMOJIS[number - 1]

    return str(number)


def format_big_number(number, _):
    if number >= 1_000_000:
        return f"{round(number / 1_000_000, 1)}M".replace(".0", "")
    elif number >= 1_000:
        return f"{round(number / 1_000, 1)}K".replace(".0", "")

    return int(number)


def quote_display(
    quote: dict,
    max_text_chars: int = 60,
    max_text_lines: int = 15,
    display_author: bool = False,
    display_status: bool = False,
    display_racers_users: bool = False,
    display_submitted_by: bool = False,
):
    """Returns a formatted string for quotes to display in embeds."""
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

    display_string += f"\"{truncate_clean(text, max_text_chars, max_text_lines)}\"\n"

    return display_string


def get_flag(user):
    country = user.get("country", None)
    return f":flag_{country.lower()}: " if country else ""


def username_with_flag(profile: dict, link_user: bool = True):
    flag = get_flag(profile)
    username = profile["username"]
    if link_user:
        return f"{flag}[{username}]({profile_url(username)})"
    else:
        return f"{flag}{escape_formatting(username)}"


def parse_number(value):
    """Parses a string into an int or float, supporting commas and K/M suffixes."""
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
