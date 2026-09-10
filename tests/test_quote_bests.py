"""A quote best is a user's best race on that quote, whichever way the list is sorted."""

import sqlite3

import pytest
import seed_data

from database.typegg import db as typegg_db
from database.typegg.users import get_quote_bests
from utils.flags import Flags

USER_ID = "quotebests"

# quoteId, wpm, pp
RACES = [
    ("fast", 320, 300),
    ("fast", 120, 100),
    ("slow", 140, 120),
    ("slow", 130, 110),
]


@pytest.fixture
def races(tmp_path):
    """Point typegg queries at a database holding two quotes with two races each."""
    patch = pytest.MonkeyPatch()
    connection = seed_data.copy_schema(typegg_db.reader, tmp_path / "typegg.db")

    connection.executemany(
        "INSERT INTO races VALUES (?, ?, ?, NULL, 1, ?, ?, ?, ?, 10, 100, 0, 0, 1750000000, 0, NULL)",
        [
            (f"{quote_id}-{wpm}", quote_id, USER_ID, pp, pp, wpm, wpm)
            for quote_id, wpm, pp in RACES
        ],
    )
    connection.commit()

    patch.setattr(typegg_db, "reader", connection)
    patch.setattr(typegg_db, "writer", connection)
    yield connection

    patch.undo()
    connection.close()


def bests(**kwargs) -> list[sqlite3.Row]:
    """Return the quote bests for the seeded user."""
    return get_quote_bests(USER_ID, columns=["quoteId", "wpm", "pp"], flags=Flags(), **kwargs)


def test_a_quote_best_is_the_fastest_race_when_sorting_ascending(races) -> None:
    """Reverse orders the list. It must not turn each quote best into a personal worst."""
    results = bests(order_by="wpm", reverse=False)

    assert [(row["quoteId"], row["wpm"]) for row in results] == [("slow", 140), ("fast", 320)]


def test_a_range_matches_a_quote_the_user_has_ever_hit(races) -> None:
    """`-worst >300 wpm` must keep a quote whose best race cleared 300."""
    results = bests(order_by="wpm", reverse=False, min_value=300)

    assert [row["quoteId"] for row in results] == ["fast"]


def test_a_range_filters_the_metric_it_sorts_by(races) -> None:
    """The same bounds pick the pp quote, not the WPM one that also falls inside them."""
    results = bests(order_by="pp", min_value=125, max_value=310)

    assert [row["quoteId"] for row in results] == ["fast"]
