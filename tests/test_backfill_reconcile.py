"""Tests for the cap and fill reconciliation in tools/backfill_command_log.py."""

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
    log_rows = {("1", "stats"): [(100.0, "u1", "server"), (200.0, "u1", "dm")]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 2}, {"1": "u1"})

    assert capped == 0
    assert filled == 0
    assert records == [
        ("1", "u1", "stats", "server", 100.0),
        ("1", "u1", "stats", "dm", 200.0),
    ]


def test_reconcile_caps_by_dropping_the_oldest(backfill):
    log_rows = {("1", "stats"): [(300.0, None, "server"), (100.0, None, "server"), (200.0, None, "server")]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 2}, {})

    assert capped == 1
    assert filled == 0
    assert [row[4] for row in records] == [200.0, 300.0]


def test_reconcile_drops_every_row_for_a_pair_the_blob_never_counted(backfill):
    log_rows = {("1", "linegraph"): [(100.0, None, "server")]}
    records, capped, filled = backfill.reconcile(log_rows, {}, {})

    assert (capped, filled, records) == (1, 0, [])


def test_reconcile_fills_the_shortfall_with_undated_rows(backfill):
    log_rows = {("1", "stats"): [(100.0, "u1", "dm")]}
    records, capped, filled = backfill.reconcile(log_rows, {("1", "stats"): 3}, {"1": "u9"})

    assert capped == 0
    assert filled == 2
    assert records[0] == ("1", "u1", "stats", "dm", 100.0)
    # Filler inherits the pair's dominant origin and the user's current TypeGG ID.
    assert records[1:] == [("1", "u9", "stats", "dm", None)] * 2


def test_reconcile_fills_a_pair_with_no_dated_rows_at_all(backfill):
    records, capped, filled = backfill.reconcile({}, {("1", "day"): 2}, {"1": None})

    assert (capped, filled) == (0, 2)
    assert records == [("1", None, "day", "server", None)] * 2


def test_reconcile_totals_always_equal_the_blob(backfill):
    log_rows = {
        ("1", "stats"): [(100.0, None, "server")] * 5,
        ("1", "day"): [(100.0, None, "dm")],
        ("2", "linegraph"): [(100.0, None, "server")] * 3,
    }
    blob_counts = {("1", "stats"): 2, ("1", "day"): 4, ("2", "stats"): 7}
    records, capped, filled = backfill.reconcile(log_rows, blob_counts, {})

    assert len(records) == sum(blob_counts.values())
    assert capped == 3 + 3
    assert filled == 3 + 7
