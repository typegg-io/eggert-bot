from typing import Optional

from dateutil import parser

from utils import urls
from utils.errors import InvalidArgument

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

OPTION_ALIASES = {
    "pp": ["performance", "pf"],
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
    timestamp = parser.parse(date_string).timestamp()
    return f"<t:{int(timestamp)}:{style}>"


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


def truncate_clean(text, max_chars):
    """Truncates a string to a maximum character length, avoiding cutting words in the middle."""
    if len(text) <= max_chars:
        return escape_formatting(text, remove_backticks=False)
    if len(text.split(" ")) == 1:
        return escape_formatting(text[:max_chars] + "...", remove_backticks=False)

    substring = text[:max_chars]
    if " " not in substring:
        return escape_formatting(substring[:max_chars] + "...", remove_backticks=False)
    while True:
        if substring[-2].isalnum() and not substring[-1].isalnum():
            break
        substring = substring[:-1]
    substring = substring[:-1]
    substring += "..."

    return escape_formatting(substring, remove_backticks=False)


def ordinal_number(number):
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if number % 100 in [11, 12, 13]:
        suffix = "th"

    return f"{number:,}{suffix}"


def quote_description(quote):
    """Returns a formatted string for quotes to display in embeds."""
    text = quote["text"]
    return (
        f"[**{quote["source"]["title"]}**]({urls.race(quote["quoteId"])}) "
        f"| {quote["difficulty"]:.2f}★ | {len(text)}c\n"
        f"\"{truncate_clean(text, 60)}\"\n"
    )


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


def quote_display(quote):
    text = quote["text"]
    ranked = quote["ranked"]
    submitted_by = quote["submittedByUsername"]

    return (
        f"**{quote["source"]["title"]}** by **{quote["source"]["author"]}**\n"
        f"{quote["difficulty"]:.2f}★ | {len(text):,}c | "
        f"{quote["races"]:,} races | {quote["uniqueUsers"]:,} users | "
        f"{"Ranked" if ranked else "Unranked"}\n"
        f"**Submitted by:** [{submitted_by}]({urls.profile(submitted_by)}) - "
        f"{discord_date(quote["created"], "D")}\n\n"
        f"\"{truncate_clean(text, 1000)}\""
    )


def get_flag(user):
    country = user.get("country", None)
    return f":flag_{country.lower()}: " if country else ""


def username_with_flag(profile):
    flag = get_flag(profile)
    return f"{flag}{escape_formatting(profile["username"])}"
