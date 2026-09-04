"""Vendor the Go grapheme cluster golden produced by ~/gparity/run.sh.

The Go side of this lives outside the typegg repo, in a scratch module that imports
typegg/common/graphemes through a replace directive. Nothing in typegg is modified.

    bash ~/gparity/run.sh                      # on the machine holding the typegg checkout
    python tools/refresh_grapheme_golden.py

Only the resulting JSON is vendored, which is Unicode data about test strings, not Go source.
"""

import json
import os
import shutil
import sys

DEFAULT_SOURCE = r"\\wsl.localhost\Ubuntu-24.04\home\keegan\gparity\grapheme_golden.json"

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "..", "tests", "fixtures", "keystrokes", "grapheme_golden.json")


def main() -> int:
    """Copy the golden into the fixture directory. Returns a process exit code."""
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE

    if not os.path.isfile(source):
        print(f"grapheme golden not found at {source}", file=sys.stderr)
        print("run `bash ~/gparity/run.sh` first", file=sys.stderr)
        return 1

    with open(source, encoding="utf-8") as f:
        golden = json.load(f)

    if not golden:
        print("golden is empty, did the corpus load?", file=sys.stderr)
        return 1

    shutil.copyfile(source, os.path.normpath(DEST))
    print(f"vendored {len(golden)} cluster maps to {os.path.normpath(DEST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
