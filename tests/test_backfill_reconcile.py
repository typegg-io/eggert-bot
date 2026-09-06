"""Tests for the CSV read and the cap and fill reconciliation in tools/backfill_command_log.py."""

import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "tools", "backfill_command_log.py")


@pytest.fixture(scope="module")
def backfill():
    """Load the backfill script as a module, since tools/ is not a package."""
    spec = importlib.util.spec_from_file_location("backfill_command_log", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reconcile_keeps_dated_rows_that_match_the_blob(backfill):
    log_rows = {("1", "stats"): [(100.0, "u1", "server", "900"), (200.0, "u1", "dm", None)]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 2}, {"1": "u1"})

    assert capped == 0
    assert filled == 0
    assert records == [
        ("1", "u1", "stats", "server", "900", 100.0),
        ("1", "u1", "stats", "dm", None, 200.0),
    ]


def test_reconcile_caps_by_dropping_the_oldest(backfill):
    log_rows = {("1", "stats"): [(t, None, "server", "900") for t in (300.0, 100.0, 200.0)]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 2}, {})

    assert capped == 1
    assert filled == 0
    assert [row[5] for row in records] == [200.0, 300.0]


def test_reconcile_drops_every_row_for_a_pair_the_blob_never_counted(backfill):
    log_rows = {("1", "linegraph"): [(100.0, None, "server", "900")]}
    records, capped, filled = backfill.reconcile(log_rows, {}, {})

    assert (capped, filled, records) == (1, 0, [])


def test_reconcile_fills_the_shortfall_with_undated_rows(backfill):
    log_rows = {("1", "stats"): [(100.0, "u1", "dm", None)]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 3}, {"1": "u9"})

    assert capped == 0
    assert filled == 2
    assert records[0] == ("1", "u1", "stats", "dm", None, 100.0)
    # Filler inherits the pair's dominant origin and the user's current TypeGG ID.
    assert records[1:] == [("1", "u9", "stats", "dm", None, None)] * 2


def test_reconcile_fills_a_pair_with_no_dated_rows_at_all(backfill):
    records, capped, filled = backfill.reconcile({}, {("1", "day"): 2}, {"1": None})

    assert (capped, filled) == (0, 2)
    assert records == [("1", None, "day", "server", None, None)] * 2


def test_reconcile_fills_with_the_pair_dominant_server(backfill):
    log_rows = {("1", "stats"): [(100.0, None, "server", "900"), (200.0, None, "server", "900")]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 3}, {})

    assert filled == 1
    assert records[-1] == ("1", None, "stats", "server", "900", None)


def test_reconcile_totals_always_equal_the_blob(backfill):
    log_rows = {
        ("1", "stats"): [(100.0, None, "server", "900")] * 5,
        ("1", "day"): [(100.0, None, "dm", None)],
        ("2", "linegraph"): [(100.0, None, "server", "900")] * 3,
    }
    blob_counts = {("1", "stats"): 2, ("1", "day"): 4, ("2", "stats"): 7}
    records, capped, filled = backfill.reconcile(log_rows, blob_counts, {})

    assert len(records) == sum(blob_counts.values())
    assert capped == 3 + 3
    assert filled == 3 + 7


def write_csv(tmp_path, rows):
    """Write a scrape CSV holding the given rows and return its path."""
    path = tmp_path / "log_history.csv"
    header = "timestamp,discord_id,user_id,server_id,channel_id,command,matched\n"
    path.write_text(header + "".join(",".join(row) + "\n" for row in rows), encoding="utf-8")
    return str(path)


def test_read_log_rows_nulls_the_dm_sentinel(backfill, tmp_path):
    csv_path = write_csv(tmp_path, [
        ("2026-01-01T00:00:00+00:00", "1", "u1", "dm", "c1", "-stats", "true"),
        ("2026-01-01T00:01:00+00:00", "1", "u1", "900", "c2", "-stats", "true"),
    ])

    rows, dropped = backfill.read_log_rows(csv_path, {"stats": "stats"})

    assert [(row[2], row[3]) for row in rows[("1", "stats")]] == [("dm", None), ("server", "900")]
    assert dropped == {}


def test_read_log_rows_skips_what_it_cannot_place(backfill, tmp_path):
    csv_path = write_csv(tmp_path, [
        ("2026-01-01T00:00:00+00:00", "1", "u1", "900", "c1", "-stats", "false"),
        ("2026-01-01T00:00:00+00:00", "1", "u1", "900", "c1", "-nosuch", "true"),
        ("2026-01-01T00:00:00+00:00", "", "u1", "900", "c1", "-stats", "true"),
    ])

    rows, dropped = backfill.read_log_rows(csv_path, {"stats": "stats"})

    assert rows == {}
    assert dropped == {"unmatched": 1, "unknown command": 1, "no discord id": 1}
