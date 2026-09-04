"""Shared comparison logic for the Go/Python keystroke parity ratchet.

Imported by both tests/test_keystroke_parity.py and tests/fixtures/refresh_divergences.py, so the
test and the manifest generator can never disagree about what counts as a divergence.
"""

import json
import os

from utils.keystrokes import get_keystroke_data

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "keystrokes")

# Go and Python differ in the last bits of float arithmetic. Anything looser is a real algorithmic
# divergence, not a formatting one.
TOLERANCE = 1e-6

# Processing this one allocates without bound and dies after about a minute, while Go handles it.
# It is excluded rather than recorded, because a MemoryError takes the test runner down with it.
EXCLUDED = {"stall_flush_batch.json": "MemoryError after ~55s, Go processes it fine"}

SCALAR_FIELDS = (("wpm", "wpm"), ("raw_wpm", "raw_wpm"), ("accuracy", "accuracy"))

GRAPH_FIELDS = (("charIndex", "char_index"), ("time", "time"), ("wpm", "wpm"), ("raw", "raw"))


def load_json(*parts):
    """Read a JSON file under the fixture directory."""
    with open(os.path.join(FIXTURE_DIR, *parts), encoding="utf-8") as f:
        return json.load(f)


def load_golden():
    """Return the golden entries for every vendored fixture, excluding the unrunnable ones."""
    return [g for g in load_json("golden.json") if g["file"] not in EXCLUDED]


def load_manifest():
    """Return the recorded divergences, keyed by 'format/file'."""
    return load_json("known_divergences.json")["divergences"]


def graph_point_differs(point, sample: dict) -> bool:
    """Return whether one sampled graph point differs from its Go value."""
    for attr, key in GRAPH_FIELDS:
        actual, expected = getattr(point, attr), sample[key]
        if expected is None or actual is None:
            if expected is not actual:
                return True
        elif abs(actual - expected) > TOLERANCE:
            return True
    return False


def compare(golden: dict) -> dict:
    """Return this fixture's divergences from Go, or an empty dict when it matches."""
    raw = load_json(golden["format"], golden["file"])

    try:
        result = get_keystroke_data(raw)
    except Exception as error:
        return {"raises": type(error).__name__}

    found = {}
    for attr, key in SCALAR_FIELDS:
        actual = getattr(result, attr)
        if abs(actual - golden[key]) > TOLERANCE:
            found[key] = {"go": golden[key], "python": actual}

    points = result.keystrokesWpmGraphData
    if len(points) != golden["graph_points"]:
        found["graph_points"] = {"go": golden["graph_points"], "python": len(points)}
    elif any(graph_point_differs(points[s["index"]], s) for s in golden["graph_sample"]):
        found["graph_sample"] = True

    return found
