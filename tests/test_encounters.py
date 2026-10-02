"""Head to head encounters obey the same date range as every other command."""

from datetime import UTC, datetime

import pytest
import seed_data

from database.typegg import db as typegg_db
from database.typegg.match_results import get_encounter_stats, get_opponent_encounters
from utils.flags import Flags

USER_ID = "runner"
OPPONENT_ID = "rival"

# matchId, timestamp
MATCHES = [
    ("old", "2026-09-01T12:00:00.000Z"),
    ("new", "2026-10-02T12:00:00.000Z"),
]


@pytest.fixture
def encounters(tmp_path):
    """Point typegg queries at a database holding one match in each of two months."""
    patch = pytest.MonkeyPatch()
    connection = seed_data.copy_schema(typegg_db.reader, tmp_path / "typegg.db")

    connection.execute(
        "INSERT INTO quotes VALUES ('q1', 'source', 'text', 0, 1, 1, 'tester', 1, "
        "'2025-01-01', 'English', NULL, NULL)"
    )
    connection.executemany(
        "INSERT INTO matches VALUES (?, 'q1', ?, 'quickplay', 2)",
        MATCHES,
    )
    connection.executemany(
        "INSERT INTO match_results VALUES (?, ?, NULL, ?, 1, 100, 100, 0, 0, 500, 1, ?, 'finished', ?)",
        [
            (match_id, user_id, user_id, placement, timestamp)
            for match_id, timestamp in MATCHES
            for user_id, placement in [(USER_ID, 1), (OPPONENT_ID, 2)]
        ],
    )
    connection.commit()

    patch.setattr(typegg_db, "reader", connection)
    patch.setattr(typegg_db, "writer", connection)
    yield connection

    patch.undo()
    connection.close()


def october() -> Flags:
    """Return flags time travelled to the day of the newer match."""
    return Flags(date_range=(
        datetime(2026, 10, 2, tzinfo=UTC),
        datetime(2026, 10, 3, tzinfo=UTC),
    ))


def test_a_date_range_narrows_the_head_to_head(encounters):
    """Without this, the head to head picks a match whose races the range then hides."""
    matches = get_opponent_encounters(USER_ID, OPPONENT_ID, flags=october())

    assert [match["matchId"] for match in matches] == ["new"]


def test_no_date_range_keeps_every_encounter(encounters):
    """Time travel is off by default, so both matches count."""
    matches = get_opponent_encounters(USER_ID, OPPONENT_ID, flags=Flags())

    assert [match["matchId"] for match in matches] == ["old", "new"]


def test_a_date_range_narrows_the_opponent_list(encounters):
    """The opponent list counts the same encounters the head to head does."""
    stats = get_encounter_stats(USER_ID, flags=october())

    assert [(row["opponentId"], row["totalEncounters"]) for row in stats] == [(OPPONENT_ID, 1)]
