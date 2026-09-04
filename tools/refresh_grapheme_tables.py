"""Regenerate src/utils/grapheme_tables.py from typegg's common/graphemes/tables.go.

The tables are Unicode character data, generated on the typegg side by common/graphemes/cmd/
gen-graphemes. This reads the Go literals and writes the Python equivalent, so both sides always
agree on the Unicode version rather than inheriting whatever ships with the interpreter.

    python tools/refresh_grapheme_tables.py [path-to-typegg]

Run it whenever typegg regenerates its tables for a new Unicode release.
"""

import os
import re
import sys

DEFAULT_TYPEGG = r"\\wsl.localhost\Ubuntu-24.04\home\keegan\typegg"

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "..", "src", "utils", "grapheme_tables.py")

TABLE_RE = re.compile(r"var (\w+) = \[\]\[2\]rune\{(.*?)\n\}", re.S)
RANGE_RE = re.compile(r"\{(0x[0-9A-Fa-f]+),\s*(0x[0-9A-Fa-f]+)\}")
VERSION_RE = re.compile(r"// Unicode ([\d.]+)\.")

HEADER = '''"""Unicode ranges for grapheme cluster breaking.

Generated from typegg's common/graphemes/tables.go by tools/refresh_grapheme_tables.py.
Do not edit by hand. Unicode {version}.
"""

'''


def main() -> int:
    """Write grapheme_tables.py. Returns a process exit code."""
    typegg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TYPEGG
    source = os.path.join(typegg, "common", "graphemes", "tables.go")

    if not os.path.isfile(source):
        print(f"tables.go not found at {source}", file=sys.stderr)
        return 1

    with open(source, encoding="utf-8") as f:
        go = f.read()

    version_match = VERSION_RE.search(go)
    version = version_match.group(1) if version_match else "unknown"

    tables = TABLE_RE.findall(go)
    if not tables:
        print("no tables parsed, has the generator's output format changed?", file=sys.stderr)
        return 1

    lines = [HEADER.format(version=version)]
    total = 0
    for name, body in tables:
        ranges = RANGE_RE.findall(body)
        total += len(ranges)
        lines.append(f"{name} = (")
        for lo, hi in ranges:
            lines.append(f"    (0x{int(lo, 16):04X}, 0x{int(hi, 16):04X}),")
        lines.append(")\n")

    with open(DEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(f"wrote {len(tables)} tables, {total} ranges, Unicode {version}")
    print(f"to {os.path.normpath(DEST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
