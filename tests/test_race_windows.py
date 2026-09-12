"""Windows over a race list split on breaks, fill a period, and reach an amount."""

from utils.windows import (
    completion_windows,
    marathon_windows,
    race_times,
    session_windows,
    top_disjoint_windows,
)

# Three races a minute apart, an hour's break, then two more.
STARTS = [0.0, 60.0, 120.0, 3720.0, 3780.0]
ENDS = [30.0, 90.0, 150.0, 3750.0, 3810.0]

COUNT_BEFORE = [0.0, 1.0, 2.0, 3.0, 4.0]
COUNT_AFTER = [1.0, 2.0, 3.0, 4.0, 5.0]


def test_race_times_place_a_race_before_the_timestamp_it_stored():
    """A race's timestamp is when it ended, so its duration decides when it began."""
    races = [{"timestamp": "2026-01-01 00:01:00.000Z", "duration": 30000}]
    starts, ends = race_times(races)

    assert ends[0] - starts[0] == 30
    assert ends[0] - 60 == starts[0] - 30


def test_a_missing_duration_leaves_a_race_with_no_length():
    """A DNF can reach the window math without a duration, and must not crash it."""
    starts, ends = race_times([{"timestamp": "2026-01-01 00:00:00.000Z", "duration": None}])

    assert starts == ends


def test_a_session_breaks_on_the_gap_between_races():
    """The gap is measured from the previous race ending to the next one starting."""
    assert session_windows(STARTS, ENDS, 1800, by_time=False) == [(0, 3, 3), (3, 5, 2)]


def test_a_session_measured_by_time_spans_its_first_start_to_its_last_end():
    assert session_windows(STARTS, ENDS, 1800, by_time=True) == [(0, 3, 150.0), (3, 5, 90.0)]


def test_a_longer_break_joins_every_race_into_one_session():
    assert session_windows(STARTS, ENDS, 7200, by_time=False) == [(0, 5, 5)]


def test_a_marathon_window_holds_every_race_finishing_inside_the_period():
    """A window opens at a race's start and takes each race that ended by the period's close."""
    windows = marathon_windows(STARTS, ENDS, 200, COUNT_BEFORE, COUNT_AFTER)

    assert windows == [(0, 3, 3.0), (1, 3, 2.0), (2, 3, 1.0), (3, 5, 2.0), (4, 5, 1.0)]


def test_a_marathon_window_drops_a_stretch_that_gained_nothing():
    """No pp gained is no marathon, so a flat stretch never reaches the board."""
    flat_before = [0.0, 50.0, 50.0]
    flat_after = [50.0, 50.0, 50.0]

    windows = marathon_windows(STARTS[:3], ENDS[:3], 200, flat_before, flat_after)

    assert windows == [(0, 3, 50.0)]


def test_a_completion_window_is_the_shortest_stretch_reaching_the_target():
    """Three races span the first race's start to the third race's end."""
    windows = completion_windows(STARTS, ENDS, 3, COUNT_BEFORE, COUNT_AFTER)

    assert windows == [(0, 3, 150.0), (1, 4, 3690.0), (2, 5, 3690.0)]


def test_a_completion_window_needs_the_full_target():
    """Fewer races than the target leaves nothing to show."""
    assert completion_windows(STARTS[:2], ENDS[:2], 3, COUNT_BEFORE[:2], COUNT_AFTER[:2]) == []


def test_a_completion_window_counts_pp_gained_rather_than_races():
    """Amounts only rise, so the window shrinks from the left until the target no longer fits."""
    before = [0.0, 10.0, 30.0, 60.0]
    after = [10.0, 30.0, 60.0, 100.0]

    windows = completion_windows(STARTS[:4], ENDS[:4], 50, before, after)

    assert windows == [(1, 3, 90.0), (2, 4, 3630.0)]


def test_the_top_windows_skip_anything_overlapping_a_better_one():
    windows = [(0, 5, 9.0), (4, 8, 8.0), (5, 9, 7.0)]

    assert top_disjoint_windows(windows) == [(0, 5, 9.0), (5, 9, 7.0)]


def test_the_top_windows_stop_at_the_count_asked_for():
    windows = [(i, i + 1, float(i)) for i in range(20)]

    assert len(top_disjoint_windows(windows, count=10)) == 10
