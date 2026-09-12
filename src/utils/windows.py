"""Windows over a race list, shared by the session, marathon and fastest completion commands."""

from bisect import bisect_right
from datetime import datetime

Window = tuple[int, int, float]


def race_times(race_list: list) -> tuple[list[float], list[float]]:
    """Return the epoch second each race started and the epoch second each one ended."""
    ends = [datetime.fromisoformat(race["timestamp"]).timestamp() for race in race_list]
    starts = [
        end - (race["duration"] or 0) / 1000
        for end, race in zip(ends, race_list, strict=True)
    ]

    return starts, ends


def race_span(first: dict, last: dict) -> str:
    """Return the race number range a window covers."""
    return f"(#{first["raceNumber"]:,} – #{last["raceNumber"]:,})"


def session_windows(starts: list, ends: list, break_seconds: float, by_time: bool) -> list[Window]:
    """Return one window per session, splitting wherever the gap between races reaches the break."""
    windows = []
    session_start = 0

    for i in range(1, len(starts)):
        if starts[i] - ends[i - 1] < break_seconds:
            continue
        windows.append(_session_window(starts, ends, session_start, i, by_time))
        session_start = i

    if starts:
        windows.append(_session_window(starts, ends, session_start, len(starts), by_time))

    return windows


def _session_window(starts: list, ends: list, start: int, end: int, by_time: bool) -> Window:
    """Value a session by the time it spanned or by the races it held."""
    return start, end, (ends[end - 1] - starts[start] if by_time else end - start)


def marathon_windows(starts: list, ends: list, period: float, before: list, after: list) -> list[Window]:
    """Return every race's window over the period following its start, valued by the amount gained."""
    windows = []

    for start, start_time in enumerate(starts):
        end = bisect_right(ends, start_time + period)
        if end <= start:
            continue

        value = after[end - 1] - before[start]
        if value > 0:
            windows.append((start, end, value))

    return windows


def completion_windows(starts: list, ends: list, target: float, before: list, after: list) -> list[Window]:
    """Return the shortest window ending at each race that reaches the target amount."""
    windows = []

    for end, end_time in enumerate(ends, start=1):
        # Both amounts only ever rise, so the last start still holding the target is the shortest.
        start = bisect_right(before, after[end - 1] - target) - 1
        if 0 <= start < end:
            windows.append((start, end, end_time - starts[start]))

    return windows


def top_disjoint_windows(windows: list[Window], count: int = 10) -> list[Window]:
    """Take windows in the order given, skipping any that overlaps one already taken."""
    top = []

    for start, end, value in windows:
        if any(start < taken_end and taken_start < end for taken_start, taken_end, _ in top):
            continue

        top.append((start, end, value))
        if len(top) == count:
            break

    return top
