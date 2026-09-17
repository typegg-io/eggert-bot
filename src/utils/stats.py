"""Speed, length and performance formulas shared across commands."""

import math

from utils.errors import InvalidKeystrokeData
from utils.keystroke_codec import KeystrokeCodecError, decode_keystroke_data

# The Keegan curve, mirroring KeeganWeightedSum in typegg's leaderboard/userstate.go.
MAX_SCORING_QUOTES = 250
PP_DECAY_FACTOR = 0.97
PP_WEIGHT_DECAY_SHARE = 0.99
PP_WEIGHT_FLOOR = 0.01


def calculate_total_pp(quote_bests: list[dict] | list[float]) -> float:
    """Returns the total performance given a list of quote bests or pp values."""
    if not quote_bests:
        return 0

    if isinstance(quote_bests[0], float):
        quote_bests.sort(reverse=True)
        values = quote_bests
    else:
        quote_bests.sort(key=lambda x: -x["pp"])
        values = [quote["pp"] for quote in quote_bests]

    total = 0.0
    for i, value in enumerate(values[:MAX_SCORING_QUOTES]):
        pp = math.floor(value)
        # A floored pp below 1 ends the sum, it does not skip the quote.
        if pp < 1:
            break
        total += pp * (PP_WEIGHT_DECAY_SHARE * PP_DECAY_FACTOR ** i + PP_WEIGHT_FLOOR)

    return total


def calculate_quote_bests(race_list: list[dict]) -> list[dict]:
    """Returns a list of quote bests given a list of races."""
    quote_dict = {}

    for race in race_list:
        quote_id = race["quoteId"]
        if quote_id not in quote_dict or race["wpm"] > quote_dict[quote_id]["wpm"]:
            quote_dict[quote_id] = race

    quote_bests = sorted(quote_dict.values(), key=lambda x: -x["pp"])

    return quote_bests


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


# The public API serves only the untrimmed duration, so XP has to be recomputed from keystrokes.
AFK_CAP = 1000


def calculate_non_afk_duration(keystroke_data) -> float | None:
    """Returns a race's duration in ms with each keystroke delay capped, or None if it will not decode."""
    try:
        decoded = decode_keystroke_data(keystroke_data)
    except (KeystrokeCodecError, InvalidKeystrokeData, KeyError, IndexError, TypeError):
        return None

    return sum(min(keystroke.timeDelta, AFK_CAP) for keystroke in decoded.keystrokes)
