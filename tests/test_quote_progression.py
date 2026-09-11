"""A PB progression lists each race that beat every earlier one on the quote, oldest first."""

from commands.quotes.quote import PROGRESSION_LIMIT, build_progression_page

# timestamp, wpm, pp
RACES = [
    ("2026-01-03 00:00:00.000Z", 110, 90),
    ("2026-01-01 00:00:00.000Z", 100, 80),
    ("2026-01-02 00:00:00.000Z", 105, 70),
    ("2026-01-04 00:00:00.000Z", 120, 90),
    ("2026-01-05 00:00:00.000Z", 130, 95),
]


def build_races() -> list[dict]:
    """Return the races as the row dicts -q passes around."""
    return [{"timestamp": timestamp, "wpm": wpm, "pp": pp} for timestamp, wpm, pp in RACES]


def progression_lines(ranked: bool, races: list[dict] | None = None) -> list[str]:
    """Return the numbered progression lines of the page, without its header."""
    page = build_progression_page(races or build_races(), ranked)
    return [line for line in page.description.split("\n") if line[:1].isdigit()]


def test_ranked_progression_follows_pp_and_skips_a_tie():
    """A ranked quote progresses by pp, so matching the best is not an improvement."""
    lines = progression_lines(ranked=True)

    assert [line.split(" - ")[2] for line in lines] == ["#1", "#3", "#5"]
    assert lines[0].startswith("1. 80.00 pp - 100.00 WPM")
    assert lines[1].startswith("2. 90.00 pp (+10.00) - 110.00 WPM")


def test_unranked_progression_follows_wpm():
    """An unranked quote progresses by WPM, where every race here was faster."""
    lines = progression_lines(ranked=False)

    assert len(lines) == 5
    assert lines[-1].startswith("5. 130.00 WPM (+10.00) - #5")


def test_a_long_progression_keeps_the_first_and_the_latest():
    """Past the limit the middle is summarised, so the embed stays under Discord's cap."""
    total = PROGRESSION_LIMIT + 10
    races = [
        {"timestamp": f"2026-01-01 00:{i // 60:02d}:{i % 60:02d}.000Z", "wpm": 100 + i, "pp": i}
        for i in range(total)
    ]
    page = build_progression_page(races, ranked=True)
    lines = progression_lines(ranked=True, races=races)

    assert len(lines) == PROGRESSION_LIMIT
    assert lines[0].startswith("1. ")
    assert lines[-1].startswith(f"{total}. ")
    assert "*10 more improvements*" in page.description
    assert len(page.description) < 4096
