"""Speed, length and performance formulas shared across commands."""

import math


def calculate_total_pp(quote_bests: list[dict] | list[float]) -> float:
    """Returns the total performance given a list of quote bests or pp values."""
    if not quote_bests:
        return 0

    if isinstance(quote_bests[0], float):
        quote_bests.sort(reverse=True)
        return sum(math.floor(v) * (0.97 ** i) for i, v in enumerate(quote_bests[:250]))
    else:
        quote_bests.sort(key=lambda x: -x["pp"])
        return sum(math.floor(q["pp"]) * (0.97 ** i) for i, q in enumerate(quote_bests[:250]))


def calculate_quote_bests(race_list: list[dict]) -> list[dict]:
    """Returns a list of quote bests given a list of races."""
    quote_dict = {}

    for race in race_list:
        quote_id = race["quoteId"]
        if quote_id not in quote_dict or race["wpm"] > quote_dict[quote_id]["wpm"]:
            quote_dict[quote_id] = race

    quote_bests = sorted(quote_dict.values(), key=lambda x: -x["pp"])

    return quote_bests


def calculate_quote_length(wpm, duration) -> int:
    """Returns the length of a quote given WPM and duration values."""
    return int(round(wpm * duration / 12000) + 1)


def calculate_wpm(duration, chars_typed) -> float:
    """Returns the WPM value given duration in ms and number of characters typed."""
    if duration == 0:
        return float("inf")
    return (12000 * chars_typed) / duration


def calculate_duration(wpm, chars_typed) -> float:
    """Returns the ms duration given WPM and number of characters typed."""
    return (chars_typed * 12000) / wpm if wpm else 0


def get_pauseless_delays(raw_delays: int) -> list[float]:
    """Returns a list of delays for "pauseless WPM", estimating a run with no pauses based on the average speed."""
    average = sum(raw_delays) / max(len(raw_delays), 1)
    pauseless_delays = []
    for j, time in enumerate(raw_delays):
        if time < average * 5:
            pauseless_delays.append(time)
        else:
            pauseless_delays.append(average)

    return pauseless_delays


# Level

# Ports of the constants and formulas in typegg's XP service.
XP_PER_SECOND = 2.5
LEVEL_A = 2.0
LEVEL_B = 15.0


def calculate_experience(duration) -> float:
    """Returns the XP a ranked race of a given ms duration earns."""
    return duration / 1000 * XP_PER_SECOND


def calculate_level(experience) -> float:
    """Returns the level a total XP value reaches."""
    hours = experience / XP_PER_SECOND / 3600
    return 1 + LEVEL_A * math.sqrt(hours * LEVEL_B)


def calculate_experience_for_level(level) -> float:
    """Returns the XP needed to reach a level."""
    return (level - 1) ** 2 * XP_PER_SECOND * 3600 / (LEVEL_A ** 2 * LEVEL_B)
