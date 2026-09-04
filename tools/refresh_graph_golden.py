"""Vendor the full keystroke graph golden produced by ~/gparity/run.sh.

Replaces the 25-point sample in golden.json with every point, so per-character timing can be
compared directly instead of inferred from a summary. Stored gzipped, since 50,000 points of
float text is 2.8 MB plain. Points are arrays:

    [charIndex, wordIndex, initialKeystrokeID, time, wpm, raw]

    bash ~/gparity/run.sh                   # on the machine holding the typegg checkout
    python tools/refresh_graph_golden.py
"""

import gzip
import json
import os
import sys

DEFAULT_SOURCE = r"\\wsl.localhost\Ubuntu-24.04\home\keegan\gparity\graph_golden.json"

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "..", "tests", "fixtures", "keystrokes", "graph_golden.json.gz")


def main() -> int:
    """Copy the graph golden into the fixture directory. Returns a process exit code."""
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE

    if not os.path.isfile(source):
        print(f"graph golden not found at {source}", file=sys.stderr)
        print("run `bash ~/gparity/run.sh` first", file=sys.stderr)
        return 1

    with open(source, encoding="utf-8") as f:
        golden = json.load(f)

    if not golden:
        print("golden is empty, did the fixtures load?", file=sys.stderr)
        return 1

    points = sum(len(entry["points"]) for entry in golden)

    # Gzipped: 2.8 MB of float text compresses to 1.1 MB, under the large-file hook's limit.
    dest = os.path.normpath(DEST)
    with gzip.open(dest, "wt", encoding="utf-8", newline="\n", compresslevel=9) as f:
        json.dump(golden, f, separators=(",", ":"))

    size = os.path.getsize(dest) / (1024 * 1024)
    print(f"vendored {len(golden)} fixtures, {points:,} graph points ({size:.1f} MB)")
    print(f"to {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
