"""Locate the first keystroke where the Python graph diverges from Go.

The porting aid for phase 3. A summary metric tells you that a fixture is wrong; this tells you
which keystroke it went wrong at, which is the difference between reading 640 lines and reading
five.

    python tools/graph_diff.py                     # first divergence in every fixture
    python tools/graph_diff.py keegan_5313.json    # full detail around the divergence
    python tools/graph_diff.py keegan_5313.json 20 # with 20 points of context

Needs tests/fixtures/keystrokes/graph_golden.json.gz, vendored by tools/refresh_graph_golden.py.
"""

import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from utils.keystrokes import get_keystroke_data  # noqa: E402  needs the sys.path line above

FIXTURES = os.path.join(HERE, "..", "tests", "fixtures", "keystrokes")
GOLDEN = os.path.join(FIXTURES, "graph_golden.json.gz")
TOLERANCE = 1e-6

FIELDS = ("charIndex", "wordIndex", "initialKeystrokeId", "time", "wpm", "raw")


def differs(actual, expected) -> bool:
    """Return whether one field of one point differs beyond tolerance."""
    if expected is None or actual is None:
        return expected is not actual
    return abs(actual - expected) > TOLERANCE


def point_of(python_point) -> tuple:
    """Return a Python graph point in the golden's array order."""
    return (
        python_point.charIndex,
        python_point.wordIndex,
        python_point.initialKeystrokeId,
        python_point.time,
        python_point.wpm,
        python_point.raw,
    )


def first_divergence(golden: dict):
    """Return (index, go_point, python_point) for the first differing point, or None."""
    path = os.path.join(FIXTURES, golden["format"], golden["file"])
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    try:
        points = get_keystroke_data(raw).keystrokesWpmGraphData
    except Exception as error:
        return ("raises", type(error).__name__, str(error))

    for i, expected in enumerate(golden["points"]):
        if i >= len(points):
            return (i, expected, None)
        actual = point_of(points[i])
        if any(differs(a, e) for a, e in zip(actual, expected)):
            return (i, expected, list(actual))

    if len(points) != len(golden["points"]):
        return (len(golden["points"]), None, f"python produced {len(points)} points")
    return None


def show(golden: dict, context: int) -> None:
    """Print the divergence for one fixture with surrounding points."""
    found = first_divergence(golden)
    if found is None:
        print(f"{golden['file']}: matches Go across all {len(golden['points'])} points")
        return

    index, expected, actual = found
    if index == "raises":
        print(f"{golden['file']}: raises {expected}: {actual}")
        return

    print(f"{golden['file']}: first divergence at point {index} of {len(golden['points'])}")
    print()
    print(f"  {'':>6} {'field':<20} {'go':>16} {'python':>16}")
    if expected and actual:
        for name, e, a in zip(FIELDS, expected, actual):
            mark = "  <-" if differs(a, e) else ""
            print(f"  {'':>6} {name:<20} {str(e):>16} {str(a):>16}{mark}")

    path = os.path.join(FIXTURES, golden["format"], golden["file"])
    with open(path, encoding="utf-8") as f:
        points = get_keystroke_data(json.load(f)).keystrokesWpmGraphData

    low = max(0, index - context)
    high = min(len(golden["points"]), index + context + 1)
    print()
    print(f"  {'i':>6} {'go time':>10} {'py time':>10} {'go wpm':>10} {'py wpm':>10} {'go raw':>10} {'py raw':>10}")
    for i in range(low, high):
        e = golden["points"][i]
        a = point_of(points[i]) if i < len(points) else (None,) * 6
        mark = " <-" if i == index else ""
        print(
            f"  {i:>6} {str(e[3]):>10} {str(a[3]):>10} "
            f"{_fmt(e[4]):>10} {_fmt(a[4]):>10} {_fmt(e[5]):>10} {_fmt(a[5]):>10}{mark}"
        )


def _fmt(value) -> str:
    """Format a nullable float for the table."""
    return "null" if value is None else f"{value:.3f}"


def main() -> int:
    """Print divergences. Returns a process exit code."""
    if not os.path.isfile(GOLDEN):
        print(f"graph golden not found at {os.path.normpath(GOLDEN)}", file=sys.stderr)
        print("run `bash ~/gparity/run.sh`, then tools/refresh_graph_golden.py", file=sys.stderr)
        return 1

    with gzip.open(GOLDEN, "rt", encoding="utf-8") as f:
        golden = json.load(f)

    if len(sys.argv) > 1:
        wanted = sys.argv[1]
        context = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        matches = [g for g in golden if g["file"] == wanted]
        if not matches:
            print(f"no fixture named {wanted}", file=sys.stderr)
            return 1
        show(matches[0], context)
        return 0

    clean = 0
    for entry in sorted(golden, key=lambda g: g["file"]):
        found = first_divergence(entry)
        if found is None:
            clean += 1
            continue
        index, expected, _ = found
        if index == "raises":
            print(f"  {entry['file']:<44} raises {expected}")
        else:
            total = len(entry["points"])
            pct = 100.0 * index / total if total else 0.0
            print(f"  {entry['file']:<44} diverges at point {index:>5} of {total:>5} ({pct:5.1f}%)")

    print()
    print(f"{clean} of {len(golden)} fixtures match Go across every graph point")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
