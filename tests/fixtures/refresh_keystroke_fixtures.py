"""Vendor the typegg keystroke fixtures and their Go golden results into this repo.

The Go side already generates golden results for every fixture, so this copies that work rather
than reimplementing it. Run it from the repo root after typegg regenerates its goldens:

    python tests/fixtures/refresh_keystroke_fixtures.py [path-to-typegg]

Only the codec and raw formats are vendored. The encrypted and compressed fixtures need
ENCRYPTION_KEY to load, which this repo does not have and does not want.

Regenerate the source goldens on the typegg side first, from common/:

    make golden
"""

import json
import os
import shutil
import sys

DEFAULT_TYPEGG = r"\\wsl.localhost\Ubuntu-24.04\home\keegan\typegg"
FORMATS = ("codec", "raw")

# Storing all 50k graph points costs 4 MB. Sampling keeps the corpus small while still failing on
# a graph that diverges anywhere along its length.
GRAPH_SAMPLES = 25

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "keystrokes")


def sample_graph(points: list[dict]) -> list[dict]:
    """Return up to GRAPH_SAMPLES evenly spaced points, always including the first and last."""
    if len(points) <= GRAPH_SAMPLES:
        chosen = range(len(points))
    else:
        step = (len(points) - 1) / (GRAPH_SAMPLES - 1)
        chosen = sorted({round(i * step) for i in range(GRAPH_SAMPLES)})
    return [
        {
            "index": i,
            "char_index": points[i]["char_index"],
            "time": points[i]["time"],
            "wpm": points[i]["wpm"],
            "raw": points[i]["raw"],
        }
        for i in chosen
    ]


def main() -> int:
    """Copy fixtures and write golden.json. Returns a process exit code."""
    typegg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TYPEGG
    source = os.path.join(typegg, "common", "replay", "testdata")
    golden_path = os.path.join(source, "golden_results.json")

    if not os.path.isfile(golden_path):
        print(f"golden_results.json not found under {source}", file=sys.stderr)
        print("run `make golden` in typegg/common first", file=sys.stderr)
        return 1

    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)

    entries = []
    for fmt in FORMATS:
        src_dir = os.path.join(source, fmt)
        dest_dir = os.path.join(DEST, fmt)
        shutil.rmtree(dest_dir, ignore_errors=True)
        os.makedirs(dest_dir, exist_ok=True)

        for result in (g for g in golden if g["format"] == fmt):
            name = result["file"]
            shutil.copyfile(os.path.join(src_dir, name), os.path.join(dest_dir, name))
            entries.append({
                "file": name,
                "format": fmt,
                "wpm": result["wpm"],
                "raw_wpm": result["raw_wpm"],
                "accuracy": result["accuracy"],
                "duration": result["duration"],
                "graph_points": len(result["graph_data"]),
                "graph_sample": sample_graph(result["graph_data"]),
            })

    out = os.path.join(DEST, "golden.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")

    size = os.path.getsize(out) / 1024
    print(f"vendored {len(entries)} fixtures across {len(FORMATS)} formats")
    print(f"wrote {out} ({size:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
