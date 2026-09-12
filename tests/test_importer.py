"""Tests for the race import in services/importer.py."""

import asyncio
import copy

import pytest
import seed_data

from database.typegg import db as typegg_db
from services import importer
from utils.dates import string_to_date
from utils.errors import UnknownQuote

PROFILE = {"userId": seed_data.USER_ID, "username": seed_data.USER_ID, "country": "us"}


def api_race(number: int, quote_id: str, match: dict | None = None) -> dict:
    """Return one race in the shape the races endpoint sends."""
    return {
        "raceId": f"race-{number}",
        "quoteId": quote_id,
        "userId": seed_data.USER_ID,
        "raceNumber": number,
        "pp": 100.0,
        "rawPp": 105.0,
        "wpm": 100.0,
        "rawWpm": 105.0,
        "duration": 6000,
        "accuracy": 0.98,
        "errorReactionTime": 200.0,
        "errorRecoveryTime": 400.0,
        "timestamp": f"2026-09-01T12:0{number}:00.000Z",
        "stickyStart": 0,
        "completionType": "finished",
        "gamemode": "quickplay" if match else "solo",
        "match": match,
    }


def api_match(number: int) -> dict:
    """Return a one-player match in the shape a race carries it."""
    return {
        "matchId": f"match-{number}",
        "startTime": f"2026-09-01T12:0{number - 1}:55.000Z",
        "players": [{
            "userId": seed_data.USER_ID,
            "username": seed_data.USER_ID,
            "raceNumber": number,
            "matchWpm": 100.0,
            "rawMatchWpm": 105.0,
            "matchPp": 100.0,
            "charactersTyped": 50,
            "startTime": 0,
            "accuracy": 0.98,
            "placement": 1,
            "completionType": "finished",
        }],
    }


RACES = [
    api_race(1, "live"),
    api_race(2, "gone"),
    api_race(3, "gone", api_match(3)),
]


async def fake_races(user_id: str, start_date: str | None = None, **kwargs) -> dict:
    """Return the races after a start date oldest first, or every race newest first without one."""
    races = copy.deepcopy(RACES)
    if start_date is None:
        return {"races": races[::-1]}
    return {"races": [race for race in races if string_to_date(race["timestamp"]) >= string_to_date(start_date)]}


async def fake_quote(quote_id: str, results: int | None = None) -> dict:
    """Return the live quote, and 404 on the one TypeGG deleted."""
    if quote_id == "gone":
        raise UnknownQuote(quote_id)
    return {
        "quoteId": quote_id,
        "source": {"sourceId": seed_data.SOURCE_ID},
        "text": "A quote that still exists.",
        "explicit": 0,
        "difficulty": 1.0,
        "complexity": 1.0,
        "submittedByUsername": seed_data.RIVAL_ID,
        "ranked": 1,
        "created": "2024-01-01T00:00:00.000Z",
        "language": "English",
    }


@pytest.fixture
def typegg(tmp_path, monkeypatch):
    """Point typegg.db at an empty copy holding one source, and stub the API the importer calls."""
    connection = seed_data.copy_schema(typegg_db.reader, tmp_path / "typegg.db")
    # copy_schema leaves foreign keys off, and the bug is a foreign key failure.
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"INSERT INTO sources VALUES ({seed_data.marks(6)})", [
        seed_data.SOURCE_ID, "The Regression Corpus", "A. Tester", "book", "https://example.invalid/cover.png", 1998,
    ])
    connection.commit()

    monkeypatch.setattr(typegg_db, "reader", connection)
    monkeypatch.setattr(typegg_db, "writer", connection)
    monkeypatch.setattr(importer, "get_races", fake_races)
    monkeypatch.setattr(importer, "get_quote", fake_quote)

    yield connection
    connection.close()


def column(connection, query: str) -> list:
    """Return the first column of every row a query returns."""
    return [row[0] for row in connection.execute(query)]


def test_races_on_a_deleted_quote_are_skipped_on_every_import(typegg):
    for _ in range(2):
        asyncio.run(importer.run(profile=PROFILE))

    assert column(typegg, "SELECT quoteId FROM quotes") == ["live"]
    assert column(typegg, "SELECT raceNumber FROM races") == [1]
    assert column(typegg, "SELECT matchId FROM matches") == []
