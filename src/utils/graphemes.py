"""Grapheme cluster breaking, deciding where one typed character ends and the next begins.

A port of common/graphemes/cluster.go in the typegg repo. WPM counts clusters, so both sides must
agree on every codepoint. TypeGG is the source of truth: a difference here is a bug in this file.

UAX #29 with one deliberate exception in GB9. A ZWJ joins only when it actually bridges two
pictographs, because the standard swallows every ZWJ into the cluster before it, which would score
a quote of 10,000 joiners as one character when the typist pressed 10,000 keys.

That exception is why a third-party grapheme library cannot be substituted here.
"""

from bisect import bisect_right

from utils.grapheme_tables import (
    Control,
    Extend,
    ExtendedPictographic,
    InCBConsonant,
    InCBLinker,
    Prepend,
    RegionalIndicator,
    SpacingMark,
)

# Hangul jamo classes, by codepoint arithmetic rather than a table.
L_BASE, L_END = 0x1100, 0x115F
V_BASE, V_END = 0x1160, 0x11A7
T_BASE, T_END = 0x11A8, 0x11FF
L_EXT_BASE, L_EXT_END = 0xA960, 0xA97C
V_EXT_BASE, V_EXT_END = 0xD7B0, 0xD7C6
T_EXT_BASE, T_EXT_END = 0xD7CB, 0xD7FB
S_BASE, S_END = 0xAC00, 0xD7A3
T_COUNT = 28

ZWJ = 0x200D
ZWNJ = 0x200C
CR = 0x000D
LF = 0x000A

NOT_JAMO, JAMO_L, JAMO_V, JAMO_T, JAMO_LV, JAMO_LVT = range(6)


def _starts(table):
    """Return the lower bound of every range, for binary search."""
    return [lo for lo, _ in table]


_STARTS = {id(t): _starts(t) for t in (
    Extend, SpacingMark, Prepend, Control, RegionalIndicator,
    ExtendedPictographic, InCBLinker, InCBConsonant,
)}


def in_table(table, code: int) -> bool:
    """Return whether a codepoint falls inside one of a table's ranges."""
    starts = _STARTS[id(table)]
    i = bisect_right(starts, code) - 1
    return i >= 0 and table[i][0] <= code <= table[i][1]


def is_extend(code: int) -> bool:
    """Return whether a codepoint always joins the cluster before it."""
    return in_table(Extend, code)


def is_spacing_mark(code: int) -> bool:
    """Return whether a codepoint is a spacing combining mark."""
    return in_table(SpacingMark, code)


def is_prepend(code: int) -> bool:
    """Return whether a codepoint attaches to the cluster after it."""
    return in_table(Prepend, code)


def is_control(code: int) -> bool:
    """Return whether a codepoint is a control character."""
    return in_table(Control, code)


def is_regional_indicator(code: int) -> bool:
    """Return whether a codepoint is a regional indicator symbol."""
    return in_table(RegionalIndicator, code)


def is_extended_pictographic(code: int) -> bool:
    """Return whether a codepoint is an extended pictographic character."""
    return in_table(ExtendedPictographic, code)


def is_linker(code: int) -> bool:
    """Return whether a codepoint is an indic conjunct break linker."""
    return in_table(InCBLinker, code)


def is_consonant(code: int) -> bool:
    """Return whether a codepoint is an indic conjunct break consonant."""
    return in_table(InCBConsonant, code)


def jamo_class(code: int) -> int:
    """Return the Hangul jamo class of a codepoint."""
    if (L_BASE <= code <= L_END) or (L_EXT_BASE <= code <= L_EXT_END):
        return JAMO_L
    if (V_BASE <= code <= V_END) or (V_EXT_BASE <= code <= V_EXT_END):
        return JAMO_V
    if (T_BASE <= code <= T_END) or (T_EXT_BASE <= code <= T_EXT_END):
        return JAMO_T
    if S_BASE <= code <= S_END:
        return JAMO_LV if (code - S_BASE) % T_COUNT == 0 else JAMO_LVT
    return NOT_JAMO


def hangul_joins(prev: int, cur: int) -> bool:
    """Return whether two Hangul codepoints join, covering GB6, GB7 and GB8."""
    prev_class = jamo_class(prev)
    if prev_class == JAMO_L:
        return jamo_class(cur) in (JAMO_L, JAMO_V, JAMO_LV, JAMO_LVT)
    if prev_class in (JAMO_LV, JAMO_V):
        return jamo_class(cur) in (JAMO_V, JAMO_T)
    if prev_class in (JAMO_LVT, JAMO_T):
        return jamo_class(cur) == JAMO_T
    return False


def map_clusters(text: str) -> tuple[list[int], int]:
    """Return each codepoint's cluster index and the total cluster count."""
    codes = [ord(c) for c in text]
    cp_to_cluster = [0] * len(codes)
    count = 0

    ends_pictograph = False
    after_bridge = False
    saw_consonant = False
    linker_after_consonant = False
    ri_run = 0

    for i, code in enumerate(codes):
        join = False
        prev = codes[i - 1] if i > 0 else 0

        if i == 0:
            pass
        elif prev == CR and code == LF:
            join = True
        elif is_control(prev) or prev in (CR, LF):
            pass
        elif is_control(code) or code in (CR, LF):
            pass
        elif code == ZWNJ:
            # ZWNJ is Extend, but a run of joiners has no base and each was a keypress.
            join = prev != ZWNJ and prev != ZWJ
        elif is_extend(code) or is_spacing_mark(code):
            join = True
        elif is_prepend(prev):
            join = True
        elif code == ZWJ:
            # Lookahead, so a joiner with nothing to join stands alone.
            join = ends_pictograph and i + 1 < len(codes) and is_extended_pictographic(codes[i + 1])
        elif after_bridge and is_extended_pictographic(code):
            join = True
        elif hangul_joins(prev, code):
            join = True
        elif linker_after_consonant and is_consonant(code):
            join = True
        elif is_regional_indicator(code) and ri_run % 2 == 1:
            join = True

        if join:
            count -= 1
        cp_to_cluster[i] = count
        count += 1

        if code == ZWJ:
            after_bridge = join
        elif is_extend(code) or is_spacing_mark(code):
            after_bridge = False
        else:
            after_bridge = False
            ends_pictograph = is_extended_pictographic(code)

        if is_linker(code):
            if saw_consonant:
                linker_after_consonant = True
        elif is_extend(code):
            pass
        elif is_consonant(code):
            saw_consonant = True
            linker_after_consonant = False
        else:
            saw_consonant = False
            linker_after_consonant = False

        ri_run = ri_run + 1 if is_regional_indicator(code) else 0

    return cp_to_cluster, count
