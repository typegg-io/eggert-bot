"""How -racehistory groups races into periods."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from commands.summary.racehistory import group_races

TORONTO = ZoneInfo("America/Toronto")


def race(timestamp: str, wpm: float = 100.0) -> dict:
    """Return a finished race at a UTC timestamp."""
    return {"timestamp": timestamp, "wpm": wpm, "accuracy": 0.95, "duration": 60_000}


RACES = [
    race("2026-09-01T12:00:00.000Z", 100),
    race("2026-09-01T13:00:00.000Z", 120),
    race("2026-09-02T02:00:00.000Z", 140),
    race("2026-09-02T12:00:00.000Z", 160),
]
TOTALS = [10.0, 15.0, 22.0, 30.0]


def test_days_follow_the_users_timezone():
    """A race at 2am UTC still belongs to the evening before in Toronto."""
    history = group_races(RACES, None, "day", TORONTO, None)

    assert [entry["races"] for entry in history] == [3, 1]
    assert history[0]["wpm"] == 120
    assert history[0]["playtime"] == 180


def test_pp_gained_counts_from_the_total_before_the_period():
    """Each period gains the difference between its last total and the one before it."""
    history = group_races(RACES, TOTALS, "day", UTC, None)

    assert [entry["pp"] for entry in history] == [15.0, 15.0]


def test_a_range_drops_races_but_keeps_earlier_pp():
    """A race before the range still counts toward the total the range starts from."""
    date_range = (datetime(2026, 9, 1, 12, 30, tzinfo=UTC), datetime(2026, 9, 3, tzinfo=UTC))

    history = group_races(RACES, TOTALS, "month", UTC, date_range)

    assert len(history) == 1
    assert history[0]["races"] == 3
    assert history[0]["pp"] == 20.0
