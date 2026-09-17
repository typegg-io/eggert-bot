"""Tests for the pure helpers in utils/, which take no database, API or matplotlib."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from utils.dates import current_utc_offset, format_utc_offset, is_date_like, parse_date
from utils.errors import InvalidDate, InvalidNumber
from utils.keystrokes import calculate_wpm
from utils.stats import (
    calculate_duration,
    calculate_experience,
    calculate_experience_for_level,
    calculate_level,
    calculate_non_afk_duration,
    calculate_total_pp,
)
from utils.strings import (
    escape_formatting,
    format_duration,
    get_segments,
    ordinal_number,
    parse_duration,
    parse_duration_args,
    parse_length_range,
    parse_number,
    parse_wpm_range,
    rank,
    truncate_text,
)

# parse_number

@pytest.mark.parametrize(("text", "expected"), [
    ("5", 5),
    ("0", 0),
    ("5.5", 5.5),
    ("1,234", 1234),
    ("2k", 2000),
    ("1.5k", 1500),
    ("1.5m", 1_500_000),
    ("  7  ", 7),
    ("2K", 2000),
])
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_parse_number_returns_int_for_whole_values():
    """Callers index and format on the result, so 5 must not come back as 5.0."""
    assert isinstance(parse_number("5"), int)


@pytest.mark.parametrize("text", ["abc", "", "1.2.3", "k"])
def test_parse_number_rejects_non_numbers(text):
    with pytest.raises(InvalidNumber):
        parse_number(text)


# parse_wpm_range

@pytest.mark.parametrize(("text", "expected"), [
    (">150", (150.0, None)),
    ("<120", (None, 120.0)),
    ("100-150", (100.0, 150.0)),
    (">99.5", (99.5, None)),
])
def test_parse_wpm_range(text, expected):
    assert parse_wpm_range(text) == expected


@pytest.mark.parametrize("text", ["150", "abc", ">", "100-", "-150", ">150x"])
def test_parse_wpm_range_returns_none_for_non_ranges(text):
    assert parse_wpm_range(text) is None


# parse_length_range

@pytest.mark.parametrize(("text", "expected"), [
    (">250c", (250, None)),
    ("<100c", (None, 100)),
    ("50-100c", (50, 100)),
])
def test_parse_length_range(text, expected):
    """A `c` suffix marks a range of quote lengths."""
    assert parse_length_range(text) == expected


@pytest.mark.parametrize("text", ["250c", ">250", "100-150", ">99.5c", "50-c", "c"])
def test_parse_length_range_returns_none_for_non_ranges(text):
    """A metric range, a bare length or a fractional length is not a length range."""
    assert parse_length_range(text) is None


# parse_duration

@pytest.mark.parametrize(("text", "expected"), [
    ("30s", 30),
    ("90m", 5400),
    ("1h", 3600),
    ("1d", 86400),
    ("1h30m", 5400),
    ("1d2h3m4s", 93784),
    ("  1H  ", 3600),
    ("1.5h", 5400),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", ["", "100", "abc", "30x", "1m30", "m", "30s1h"])
def test_parse_duration_returns_none_for_non_durations(text):
    """Units must appear at most once and in descending order, or it is not a duration."""
    assert parse_duration(text) is None


def test_parse_duration_args_totals_every_duration_token():
    assert parse_duration_args(["eiko", "1h", "30m"]) == 5400


def test_parse_duration_args_reads_a_token_the_flag_parser_negated():
    """A duration can reach raw_args with the flag dash still attached."""
    assert parse_duration_args(["-30m"]) == 1800


def test_parse_duration_args_returns_none_without_a_duration():
    assert parse_duration_args(["eiko", "pp"]) is None


# format_duration

@pytest.mark.parametrize(("seconds", "expected"), [
    (0, "0s"),
    (42, "42s"),
    (90, "1m 30s"),
    (3661, "1h 1m 1s"),
    (90061, "1d 1h 1m 1s"),
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_duration_without_seconds_floors_to_the_minute():
    assert format_duration(90, show_seconds=False) == "1m"
    assert format_duration(0, show_seconds=False) == "0m"


# Text helpers

def test_escape_formatting_neutralises_discord_markdown():
    escaped = escape_formatting("a *b* _d_")
    assert "*b*" not in escaped
    assert "_d_" not in escaped


def test_truncate_text_returns_the_text_and_a_count():
    text, count = truncate_text("one two three four five", 12, 5)
    assert text.endswith("...")
    assert isinstance(count, int)


def test_truncate_text_leaves_short_text_alone():
    text, _ = truncate_text("short", 100, 5)
    assert text == "short"


def test_get_segments_preserves_the_original_text():
    """Segments are rendered per word, so joining them must reproduce the input exactly."""
    for text in ["a b c", "a b  c", "hello world", "one"]:
        assert "".join(get_segments(text)) == text


@pytest.mark.parametrize(("number", "expected"), [
    (1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (21, "21st"),
])
def test_ordinal_number(number, expected):
    assert ordinal_number(number) == expected


def test_rank_uses_emoji_for_the_top_twenty_and_bold_after():
    assert rank(1).startswith(":")
    assert rank(21) == "**21**"


# Dates

@pytest.mark.parametrize("text", ["now", "today", "yesterday", "yd", "2026-01-05"])
def test_is_date_like_accepts_keywords_and_iso_dates(text):
    assert is_date_like(text)


@pytest.mark.parametrize("text", ["keegant", "raw", "500"])
def test_is_date_like_rejects_ordinary_arguments(text):
    assert not is_date_like(text)


def test_parse_date_reads_an_iso_date_as_utc_midnight():
    assert parse_date("2026-01-05") == datetime(2026, 1, 5, tzinfo=UTC)


def test_parse_date_rejects_nonsense():
    with pytest.raises(InvalidDate):
        parse_date("not-a-date")


@pytest.mark.parametrize(("offset", "expected"), [
    (timedelta(0), "UTC"),
    (timedelta(hours=-7), "UTC-7"),
    (timedelta(hours=9), "UTC+9"),
    (timedelta(hours=5, minutes=30), "UTC+5:30"),
    (timedelta(hours=5, minutes=45), "UTC+5:45"),
    (timedelta(hours=-9, minutes=-30), "UTC-9:30"),
])
def test_format_utc_offset_labels_an_offset(offset, expected):
    assert format_utc_offset(offset) == expected


def test_current_utc_offset_reads_a_zone_that_never_shifts():
    assert current_utc_offset(ZoneInfo("Asia/Kolkata")) == timedelta(hours=5, minutes=30)


# Stats

def test_wpm_and_duration_round_trip():
    """calculate_duration is the inverse of calculate_wpm for the same character count."""
    duration = calculate_duration(wpm=100, chars_typed=250)
    assert calculate_wpm(250, duration) == pytest.approx(100)


def test_calculate_wpm_is_zero_for_a_zero_duration():
    assert calculate_wpm(100, 0) == 0.0


def test_calculate_duration_is_zero_for_zero_wpm():
    assert calculate_duration(0, 100) == 0


def test_total_pp_weights_each_quote_on_the_keegan_curve():
    """Weight i is 0.99 * 0.97**i + 0.01, which leaves the top quote at full value."""
    expected = 100 + 100 * (0.99 * 0.97 + 0.01)

    assert calculate_total_pp([100.0, 100.0]) == pytest.approx(expected)


def test_total_pp_stops_at_a_quote_worth_less_than_a_point():
    """A floored pp below 1 ends the sum rather than contributing a fraction."""
    assert calculate_total_pp([50.0, 0.5]) == pytest.approx(50)


# Level

def test_an_hour_of_ranked_typing_earns_nine_thousand_xp():
    """XP is 2.5 per second, the rate typegg's XP service sets."""
    assert calculate_experience(60 * 60 * 1000) == 9000


@pytest.mark.parametrize("level", [1, 2, 10, 45, 72, 100])
def test_a_level_threshold_lands_exactly_on_that_level(level):
    """calculate_experience_for_level is the inverse of calculate_level."""
    assert calculate_level(calculate_experience_for_level(level)) == pytest.approx(level)



def legacy_keystrokes(*deltas: int) -> dict:
    """Return a legacy keystroke payload typing "ab" with the given delays."""
    return {
        "text": "ab",
        "keystrokes": [
            {"action": {"i": index, "key": key}, "time": sum(deltas[:index + 1]), "timeDelta": delta}
            for index, (key, delta) in enumerate(zip("ab", deltas, strict=True))
        ],
    }


def test_an_idle_keystroke_counts_as_one_second():
    """XP trims AFK time the way typegg's replay ingest does."""
    assert calculate_non_afk_duration(legacy_keystrokes(200, 60000)) == 1200


def test_an_undecodable_payload_has_no_non_afk_duration():
    """A NULL lets readers fall back to the untrimmed duration."""
    assert calculate_non_afk_duration([9, "text", 0, "junk"]) is None
