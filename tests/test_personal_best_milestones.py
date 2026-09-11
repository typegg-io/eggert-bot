"""Every personal best is listed, and a milestone tags the ones that crossed a step boundary."""

from commands.graphs.personalbestgraph import (
    PROGRESSION_LIMIT,
    build_progression_lines,
    find_milestones,
    find_personal_bests,
)

VALUES = [95, 92, 101, 101, 104, 128, 129.99, 130]


def build_races(values: list[float]) -> list[dict]:
    """Return one race row per value, numbered from one."""
    return [
        {"wpm": value, "raceNumber": i + 1, "timestamp": f"2026-01-01 00:{i // 60:02d}:{i % 60:02d}.000Z"}
        for i, value in enumerate(values)
    ]


def progression_lines(values: list[float], over_time: bool = False, races: list[dict] | None = None) -> list[str]:
    """Return the progression lines for one page over the given values."""
    bests = find_personal_bests(values)
    milestones = find_milestones(values, bests, 10)
    return build_progression_lines(races or build_races(values), "wpm", bests, milestones, over_time)


def test_personal_bests_skip_slower_races_and_ties():
    """Only a strictly higher value is a new best."""
    assert find_personal_bests(VALUES) == [0, 2, 4, 5, 6, 7]


def test_a_jump_is_labelled_with_the_highest_barrier_it_broke():
    """Jumping from 104 to 128 breaks 110 and 120, and only 120 is reported."""
    bests = find_personal_bests(VALUES)

    assert find_milestones(VALUES, bests, 10) == [(2, 100), (5, 120), (7, 130)]


def test_every_best_gets_a_line_and_only_milestones_are_tagged():
    """A best that broke no milestone is still listed, just without a tag."""
    assert progression_lines(VALUES) == [
        "95.00 WPM - #1",
        "101.00 WPM - #3 - **Broke 100**",
        "104.00 WPM - #5",
        "128.00 WPM - #6 - **Broke 120**",
        "129.99 WPM - #7",
        "130.00 WPM - #8 - **Broke 130**",
    ]


def test_the_time_page_shows_dates_instead_of_race_numbers():
    """Each page carries one locator, so a line stays short enough not to wrap."""
    lines = progression_lines(VALUES, over_time=True)

    assert lines[1].startswith("101.00 WPM - <t:")
    assert lines[1].endswith(":D> - **Broke 100**")
    assert not any("#" in line for line in lines)


def test_a_race_without_a_number_still_gets_a_line():
    """An unnumbered race drops only its race number."""
    races = build_races(VALUES)
    races[-1]["raceNumber"] = None

    assert progression_lines(VALUES, races=races)[-1] == "130.00 WPM - **Broke 130**"


def test_a_long_career_keeps_the_first_and_the_latest():
    """Past the limit the middle is summarised, so the embed stays under Discord's cap."""
    values = list(range(0, 1000, 10))
    lines = progression_lines(values, over_time=True)

    assert len(lines) == PROGRESSION_LIMIT + 1
    assert lines[0].startswith("0.00 WPM - ")
    assert "*50 more improvements*" in lines
    assert lines[-1].startswith("990.00 WPM - ")
    assert len("\n".join(lines)) < 4000
