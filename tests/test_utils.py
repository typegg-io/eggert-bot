"""Tests for the pure helpers in utils/, which take no database, API or matplotlib."""

from datetime import UTC, datetime

import pytest

from utils.dates import is_date_like, parse_date
from utils.errors import InvalidDate, InvalidNumber
from utils.stats import calculate_duration, calculate_quote_length, calculate_wpm
from utils.strings import (
    escape_formatting,
    format_duration,
    get_segments,
    ordinal_number,
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


# Stats

def test_wpm_and_duration_round_trip():
    """calculate_duration is the inverse of calculate_wpm for the same character count."""
    duration = calculate_duration(wpm=100, chars_typed=250)
    assert calculate_wpm(duration, 250) == pytest.approx(100)


def test_calculate_wpm_is_infinite_for_a_zero_duration():
    assert calculate_wpm(0, 100) == float("inf")


def test_calculate_duration_is_zero_for_zero_wpm():
    assert calculate_duration(0, 100) == 0


def test_calculate_quote_length_is_positive():
    assert calculate_quote_length(wpm=100, duration=30000) > 0
