"""Differential tests for the keystroke engine against the Go reference.

utils/keystrokes.py and utils/keystroke_codec.py are ports of common/keystroke/ and
common/replay/ in the typegg repo. TypeGG is the source of truth: a difference here is a bug in
the Python, never a reason to change the Go.

The port currently diverges on most fixtures, so this is a ratchet rather than a pass/fail gate.
known_divergences.json records exactly what differs today. A fixture that starts diverging fails,
and so does one that quietly stops, which forces the manifest to shrink as the port is corrected.

Fixtures and expected values are vendored from typegg's own goldens:

    python tests/fixtures/refresh_keystroke_fixtures.py   # after `make golden` in typegg/common
    python tests/fixtures/refresh_divergences.py          # after fixing the port
"""

import pytest
from keystroke_diff import EXCLUDED, compare, load_golden, load_manifest

GOLDEN = load_golden()
MANIFEST = load_manifest()
CASES = [pytest.param(g, id=f"{g['format']}/{g['file']}") for g in GOLDEN]


def test_the_corpus_is_present():
    """Guard against a refresh that silently vendored nothing."""
    assert len(GOLDEN) >= 79


def test_the_manifest_only_names_real_fixtures():
    """A renamed or dropped fixture must break the manifest instead of silently disabling it."""
    known = {f"{g['format']}/{g['file']}" for g in GOLDEN}
    assert sorted(set(MANIFEST) - known) == []


def test_excluded_fixtures_are_documented():
    """Anything skipped outright carries the reason it cannot run."""
    assert all(isinstance(reason, str) and reason for reason in EXCLUDED.values())


@pytest.mark.parametrize("golden", CASES)
def test_matches_go_or_diverges_exactly_as_recorded(golden):
    """Compare one fixture against Go and against what we already know differs."""
    key = f"{golden['format']}/{golden['file']}"
    expected = MANIFEST.get(key, {})
    actual = compare(golden)

    new = sorted(set(actual) - set(expected))
    fixed = sorted(set(expected) - set(actual))

    assert new == [], (
        f"{key} gained divergences {new}. "
        f"This is a regression in the port, not something to record."
    )
    assert fixed == [], (
        f"{key} no longer diverges on {fixed}. "
        f"Run tests/fixtures/refresh_divergences.py to shrink the manifest."
    )


def test_parity_progress_is_reported(record_property):
    """Surface how much of the corpus still diverges, so progress is visible in CI output."""
    total = len(GOLDEN)
    diverging = len(MANIFEST)
    record_property("keystroke_parity_matching", total - diverging)
    record_property("keystroke_parity_total", total)
    assert diverging <= len(MANIFEST)
