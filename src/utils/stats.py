def calculate_total_pp(quote_bests: list[dict]):
    """Returns the total performance given a list of quote bests."""
    return sum(q["pp"] * (0.97 ** i) for i, q in enumerate(quote_bests))


def calculate_quote_bests(race_list: list[dict]):
    """Returns a list of quote bests given a list of races."""
    quote_dict = {}

    for race in race_list:
        quote_id = race["quoteId"]
        if quote_id not in quote_dict or race["wpm"] > quote_dict[quote_id]["wpm"]:
            quote_dict[quote_id] = race

    quote_bests = sorted(quote_dict.values(), key=lambda x: -x["pp"])

    return quote_bests


def calculate_quote_length(wpm, duration):
    """Returns the length of a quote given WPM and duration values."""
    return int(round(wpm * duration / 12000) + 1)


def calculate_ms(quote, wpm):
    if wpm == 0: return 0
    return round((len(quote) * 12000) / wpm)


def calculate_wpm(duration, chars_typed):
    """Returns the WPM value given duration in ms and number of characters typed."""
    return (12000 * chars_typed) / duration


def calculate_duration(wpm, chars_typed):
    """Returns the ms duration given WPM and number of characters typed."""
    return (chars_typed * 12000) / wpm
