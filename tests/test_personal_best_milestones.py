"""A milestone is the highest step boundary a personal best crossed that the previous best had not."""

from commands.graphs.personalbestgraph import (
    MILESTONE_LIMIT,
    build_milestone_lines,
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


def test_personal_bests_skip_slower_races_and_ties():
    """Only a strictly higher value is a new best."""
    assert find_personal_bests(VALUES) == [0, 2, 4, 5, 6, 7]


def test_a_jump_is_labelled_with_the_highest_barrier_it_broke():
    """Jumping from 104 to 128 breaks 110 and 120, and only 120 is reported."""
    bests = find_personal_bests(VALUES)

    assert find_milestones(VALUES, bests, 10) == [(2, 100), (5, 120), (7, 130)]


def test_the_best_race_is_marked_on_its_milestone_line():
    """When the best race broke a milestone, no separate Best line repeats it."""
    races = build_races(VALUES)
    bests = find_personal_bests(VALUES)
    lines = build_milestone_lines(races, "wpm", bests, find_milestones(VALUES, bests, 10))

    assert [line.split(":**")[0] for line in lines] == [
        "**First Race", "**Broke 100 WPM", "**Broke 120 WPM", "**Broke 130 WPM (Best)",
    ]
    assert "Race #8 " in lines[-1]


def test_a_best_short_of_a_milestone_gets_its_own_line():
    """A best that broke nothing still closes the list."""
    values = VALUES[:-1]
    races = build_races(values)
    bests = find_personal_bests(values)
    lines = build_milestone_lines(races, "wpm", bests, find_milestones(values, bests, 10))

    assert lines[-1].startswith("**Best:** 129.99 WPM - Race #7 ")


def test_a_race_without_a_number_still_gets_a_line():
    """An unnumbered race drops only its race number."""
    races = build_races(VALUES)
    races[-1]["raceNumber"] = None
    bests = find_personal_bests(VALUES)
    lines = build_milestone_lines(races, "wpm", bests, find_milestones(VALUES, bests, 10))

    assert lines[-1].startswith("**Broke 130 WPM (Best):** 130.00 WPM - <t:")


def test_a_long_career_keeps_the_first_and_the_latest():
    """Past the limit the middle is summarised, so the embed stays under Discord's cap."""
    values = list(range(0, 1000, 10))
    races = build_races(values)
    bests = find_personal_bests(values)
    lines = build_milestone_lines(races, "wpm", bests, find_milestones(values, bests, 10))

    assert len(lines) == MILESTONE_LIMIT + 1
    assert lines[0].startswith("**First Race:**")
    assert lines[-1].startswith("**Broke 990 WPM (Best):**")
    assert len("\n".join(lines)) < 4000
