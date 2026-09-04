"""Tests for grapheme cluster breaking, the unit WPM counts.

utils/graphemes.py is a port of common/graphemes/cluster.go. The rules are UAX #29 with one
deliberate exception in GB9, so these pin the exception as much as the standard.

The parity test against Go is skipped until the golden is vendored. Generate it with:

    bash ~/gparity/run.sh          # on the machine that has the typegg checkout
    python tools/refresh_grapheme_golden.py
"""

import json
import os

import pytest

from utils.graphemes import map_clusters

GOLDEN = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "keystrokes", "grapheme_golden.json"
)


def clusters(text: str) -> int:
    """Return the cluster count for a string."""
    return map_clusters(text)[1]


@pytest.mark.parametrize(("text", "expected"), [
    ("", 0),
    ("a", 1),
    ("abc", 3),
])
def test_ascii_is_one_cluster_per_character(text, expected):
    assert clusters(text) == expected


def test_combining_marks_join_the_base():
    assert clusters("tést") == 4
    assert clusters("x̀́y") == 2


def test_precomposed_and_decomposed_agree_on_count():
    assert clusters("tést") == clusters("tést")


def test_regional_indicators_pair_into_flags():
    """GB12 and GB13 pair them up, so a third starts a new flag."""
    assert clusters("\U0001F1EC\U0001F1E7") == 1
    assert clusters("\U0001F1EC\U0001F1E7\U0001F1EC") == 2
    assert clusters("\U0001F1EC\U0001F1E7\U0001F1EC\U0001F1E7") == 2


def test_zwj_sequence_is_one_cluster():
    assert clusters("\U0001F468‍\U0001F469‍\U0001F467") == 1


def test_a_zwj_that_bridges_nothing_stands_alone():
    """The GB9 exception. UAX #29 would swallow the joiner, which would score keypresses as free."""
    assert clusters("a‍") == 2
    assert clusters("‍") == 1
    assert clusters("a‍b") == 3


def test_a_zwnj_run_does_not_collapse():
    """ZWNJ is Extend, but a run of joiners has no base and each one was a keypress."""
    assert clusters("a‌b") == 2
    assert clusters("a‌‌b") == 3


def test_hangul_jamo_compose_into_one_syllable():
    assert clusters("각") == 1
    assert clusters("각") == 1
    assert clusters("가") == 1


def test_crlf_is_one_cluster():
    assert clusters("a\r\nb") == 3
    assert clusters("a\rb") == 3


def test_cluster_map_is_monotonic_and_covers_every_codepoint():
    """Each codepoint maps to its cluster, so the map never goes backwards."""
    for text in ("abc", "tést", "\U0001F1EC\U0001F1E7\U0001F1EC", "각"):
        mapping, count = map_clusters(text)
        assert len(mapping) == len(text)
        assert mapping == sorted(mapping)
        assert (max(mapping) + 1 if mapping else 0) == count


@pytest.mark.skipif(not os.path.isfile(GOLDEN), reason="grapheme golden not vendored yet")
def test_matches_the_go_reference():
    """Every string in the corpus clusters exactly as typegg's Go does."""
    with open(GOLDEN, encoding="utf-8") as f:
        golden = json.load(f)

    assert golden, "golden is empty"

    mismatches = []
    for entry in golden:
        mapping, count = map_clusters(entry["text"])
        if count != entry["count"] or mapping != entry["map"]:
            mismatches.append(
                f"{entry['text']!r}: go count={entry['count']} map={entry['map']} "
                f"python count={count} map={mapping}"
            )
    assert mismatches == []
