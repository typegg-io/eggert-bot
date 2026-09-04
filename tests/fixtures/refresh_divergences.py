"""Regenerate the manifest of known Go/Python keystroke divergences.

The manifest is a ratchet. The parity test fails if a fixture not listed diverges, and also fails
if a listed fixture has started matching, which forces its entry to be deleted as the port is
fixed. Shrinking this file is the whole of phase 3.

    python tests/fixtures/refresh_divergences.py

Only run this to record a genuine, understood change. Regenerating it to turn a red suite green
defeats the point.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "src"), os.path.join(HERE, "..")]

from keystroke_diff import EXCLUDED, FIXTURE_DIR, compare, load_golden  # noqa: E402  needs sys.path above


def main() -> int:
    """Write known_divergences.json. Returns a process exit code."""
    manifest = {}
    golden = load_golden()

    for entry in golden:
        found = compare(entry)
        if found:
            manifest[f"{entry['format']}/{entry['file']}"] = found

    out = os.path.join(FIXTURE_DIR, "known_divergences.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"excluded": EXCLUDED, "divergences": manifest}, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"{len(manifest)} of {len(golden)} fixtures diverge from Go")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
