"""Tests for reading keystroke payloads back out of typegg.db."""

import json
import sqlite3
import zlib

import pytest

from database.typegg import db, keystroke_data

PAYLOAD = [{"key": "a", "time": 100}, {"key": "b", "time": 220}]


@pytest.fixture
def scratch_typegg(tmp_path, monkeypatch):
    """Point typegg.db queries at an empty database carrying the real schema."""
    schema = db.reader.execute("""
        SELECT sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
    """).fetchall()

    connection = sqlite3.connect(tmp_path / "typegg.db")
    connection.row_factory = sqlite3.Row
    for (statement,) in schema:
        connection.execute(statement)
    connection.commit()

    monkeypatch.setattr(db, "reader", connection)
    monkeypatch.setattr(db, "writer", connection)
    yield connection
    connection.close()


def store(connection, race_id, compressed):
    """Insert one keystroke row the way the importer or the compressor would leave it."""
    blob = json.dumps(PAYLOAD)
    if compressed:
        blob = zlib.compress(blob.encode("utf-8"), level=6)

    connection.execute("""
        INSERT INTO keystroke_data (raceId, keystrokeData, compressed) VALUES (?, ?, ?)
    """, [race_id, blob, int(compressed)])
    connection.commit()


def test_reads_an_uncompressed_payload(scratch_typegg):
    store(scratch_typegg, "r1", compressed=False)

    assert keystroke_data.get_keystroke_data("r1") == PAYLOAD


def test_reads_a_compressed_payload(scratch_typegg):
    store(scratch_typegg, "r1", compressed=True)

    assert keystroke_data.get_keystroke_data("r1") == PAYLOAD


def test_a_race_with_no_keystrokes_reads_as_none(scratch_typegg):
    assert keystroke_data.get_keystroke_data("missing") is None


def test_compressing_a_row_leaves_it_readable(scratch_typegg):
    store(scratch_typegg, "r1", compressed=False)

    assert keystroke_data.get_uncompressed_count() == 1
    assert keystroke_data.compress_batch() == 1
    assert keystroke_data.get_uncompressed_count() == 0
    assert keystroke_data.get_keystroke_data("r1") == PAYLOAD
