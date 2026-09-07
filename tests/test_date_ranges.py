"""Tests for the date range that time travel and the date flags resolve to.

resolve_date_range runs after the user loads, so it is the only place that knows both the tokens
the user typed and the timezone they are typed in.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from bot_setup import parse_flags
from utils.dates import resolve_date_range

NEW_YORK = ZoneInfo("America/New_York")


def resolve(content, tz=NEW_YORK, stored=(None, None)):
    """Return the local start and end a message resolves to."""
    date_range = resolve_date_range(parse_flags(content)[0], tz, stored)
    if date_range is None:
        return None

    return tuple(date.astimezone(tz) for date in date_range)


def local(year, month, day, tz=NEW_YORK):
    """Return local midnight on a date."""
    return datetime(year, month, day, tzinfo=tz)

def elapsed_hours(date_range) -> float:
    """Return the real hours a range covers, which a same-zone subtraction would not give."""
    start, end = (date.astimezone(UTC) for date in date_range)
    return (end - start).total_seconds() / 3600



def test_no_dates_and_no_stored_range_means_all_time():
    assert resolve("-best") is None


def test_a_stored_range_applies_when_nothing_is_typed():
    stored = (local(2025, 9, 1).timestamp(), local(2026, 9, 1).timestamp())
    assert resolve("-best", stored=stored) == (local(2025, 9, 1), local(2026, 9, 1))


def test_alltime_suppresses_a_stored_range():
    stored = (local(2025, 9, 1).timestamp(), local(2026, 9, 1).timestamp())
    assert resolve("-best alltime", stored=stored) is None


def test_typed_dates_beat_a_stored_range():
    stored = (local(2020, 1, 1).timestamp(), local(2021, 1, 1).timestamp())
    assert resolve("-best 3/1/2025 3/2/2025", stored=stored) == (local(2025, 3, 1), local(2025, 3, 3))


def test_the_end_date_includes_all_of_its_own_day():
    assert resolve("-best 1/1/2026 1/1/2026") == (local(2026, 1, 1), local(2026, 1, 2))


def test_a_typed_date_is_read_in_the_users_timezone():
    """parse_date returns UTC midnight, which is the day before west of UTC."""
    assert resolve("-best 9/1/2025 9/1/2026")[0] == local(2025, 9, 1)


def test_a_range_spanning_a_dst_change_keeps_both_endpoints_at_midnight():
    start, end = resolve("-best 3/8/2025 3/9/2025")
    assert (start, end) == (local(2025, 3, 8), local(2025, 3, 10))
    assert start.utcoffset() != end.utcoffset()


def test_year_snaps_to_january_first_in_the_users_timezone():
    start, end = resolve("-best year")
    assert (start.month, start.day, start.hour) == (1, 1, 0)
    assert end.year == start.year + 1


def test_year_is_not_the_last_365_days():
    start, _ = resolve("-best year")
    assert start == local(datetime.now(UTC).astimezone(NEW_YORK).year, 1, 1)


def test_a_period_anchors_on_the_date_typed():
    assert resolve("-best month 2025-03-15")[0] == local(2025, 3, 1)


def test_day_anchors_on_the_date_typed_rather_than_the_day_before():
    assert resolve("-best day 2025-03-09")[0] == local(2025, 3, 9)


def test_week_floors_to_monday():
    assert resolve("-best week 2025-03-12")[0] == local(2025, 3, 10)


def test_dates_typed_in_reverse_order_are_sorted():
    assert resolve("-best 9/1/2026 9/1/2025") == (local(2025, 9, 1), local(2026, 9, 2))

def test_a_period_day_is_twenty_five_hours_long_when_the_clocks_go_back():
    assert elapsed_hours(resolve("-best day 2025-11-02")) == 25


def test_a_period_day_is_twenty_three_hours_long_when_the_clocks_go_forward():
    assert elapsed_hours(resolve("-best day 2025-03-09")) == 23
