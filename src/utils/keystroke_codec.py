"""Keystroke codec — decodes compact [version, text, stickyStart, keystrokesStr] arrays
and the legacy {text, keystrokes, isStickyStart} dict form into KeystrokeData.

Compact encoding: actions joined by '|', each "{timeDelta}[modifier]{code}{params}".
Action codes: ^ (composition), + (insert), > (insert-at), < (backspace),
- (delete-range), = (replace), ~ (redundant replace). Parsed codepoint-for-codepoint.
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Union

CODEC_VERSION = 2
SEP_KEYSTROKE = "|"
SEP_PARAM = ","

# Modifier prefix characters
_INSERT_MODIFIERS = frozenset({"L", "R", "S", "C", "V"})
_DELETE_MODIFIERS = frozenset({"X", "M"})


class KeystrokeCodecError(Exception):
    """Raised on malformed encoded keystroke data."""


@dataclass
class KeystrokeInsert:
    i: int
    key: str
    mod: Optional[str] = None


@dataclass
class KeystrokeDelete:
    dStart: int
    dEnd: int
    mod: Optional[str] = None


@dataclass
class KeystrokeReplace:
    rStart: int
    rEnd: int
    key: str = ""
    redundant: Optional[bool] = None
    mod: Optional[str] = None


@dataclass
class KeystrokeComposition:
    i: int
    key: str
    steps: List[str] = field(default_factory=list)
    stepTimes: List[int] = field(default_factory=list)


KeystrokeAction = Union[
    KeystrokeInsert, KeystrokeDelete, KeystrokeReplace, KeystrokeComposition
]


@dataclass
class Keystroke:
    action: KeystrokeAction
    time: int
    timeDelta: int


@dataclass
class KeystrokeData:
    text: str
    keystrokes: List[Keystroke]
    isStickyStart: bool = False


_WORD_BREAK_CHARS = (" ", "\n", "⏎")


def _normalize_newlines(s: str) -> str:
    return s.replace("⏎", "\n").replace("\r\n", "\n")


def _find_word_break(remaining: str) -> int:
    best = -1
    for ch in _WORD_BREAK_CHARS:
        idx = remaining.find(ch)
        if idx >= 0 and (best < 0 or idx < best):
            best = idx
    return best


def simulate_word_completion(input_val: str, text: str, completed_chars: int) -> tuple[str, int]:
    """Slice completed words off ``input_val``, advancing ``completed_chars``.

    Input uses '⏎' for newlines; text uses '\\n' or '\\r\\n' — both sides are
    normalized for comparison, but the char count advances by the raw text-word length.
    """
    if not text[completed_chars:]:
        return input_val, completed_chars

    while input_val:
        remaining = text[completed_chars:]
        if not remaining:
            break

        break_idx = _find_word_break(remaining)
        if break_idx < 0:
            break

        word = remaining[: break_idx + 1]
        if not word:
            break

        norm_input = unicodedata.normalize("NFC", _normalize_newlines(input_val))
        norm_word = unicodedata.normalize("NFC", _normalize_newlines(word))
        if len(norm_input) >= len(norm_word) and norm_input[: len(norm_word)] == norm_word:
            slice_len = len(word) if len(word) == len(norm_word) else len(norm_word)
            input_val = input_val[slice_len:]
            completed_chars += len(word)
        else:
            break

    return input_val, completed_chars


_DIGITS = frozenset("0123456789")


def _read_key_until_delimiter(chars: List[str], idx: int) -> tuple[str, int]:
    """Read codepoints until the next '|' (or end). If the first char IS '|',
    the key is literally '|'.
    """
    if idx >= len(chars):
        return "", idx
    if chars[idx] == SEP_KEYSTROKE:
        return "|", idx + 1
    parts: List[str] = []
    while idx < len(chars) and chars[idx] != SEP_KEYSTROKE:
        parts.append(chars[idx])
        idx += 1
    return "".join(parts), idx


def _decode_legacy_dict(parsed: dict) -> KeystrokeData:
    text = unicodedata.normalize("NFC", parsed.get("text", "").replace("\r\n", "\n"))
    ks_raw = parsed.get("keystrokes", [])
    keystrokes: List[Keystroke] = []
    for ks in ks_raw:
        action_dict = ks.get("action", {})
        action: KeystrokeAction
        if "steps" in action_dict:
            action = KeystrokeComposition(
                i=action_dict.get("i", 0),
                key=action_dict.get("key", ""),
                steps=list(action_dict.get("steps", [])),
                stepTimes=list(action_dict.get("stepTimes", [])),
            )
        elif "i" in action_dict:
            action = KeystrokeInsert(
                i=action_dict["i"],
                key=action_dict.get("key", ""),
                mod=action_dict.get("mod"),
            )
        elif "dStart" in action_dict:
            action = KeystrokeDelete(
                dStart=action_dict["dStart"],
                dEnd=action_dict["dEnd"],
                mod=action_dict.get("mod"),
            )
        elif "rStart" in action_dict:
            action = KeystrokeReplace(
                rStart=action_dict["rStart"],
                rEnd=action_dict["rEnd"],
                key=action_dict.get("key", ""),
                redundant=action_dict.get("redundant"),
                mod=action_dict.get("mod"),
            )
        else:
            raise KeystrokeCodecError(f"Unknown action shape: {action_dict}")
        keystrokes.append(
            Keystroke(action=action, time=ks.get("time", 0), timeDelta=ks.get("timeDelta", 0))
        )
    return KeystrokeData(
        text=text,
        keystrokes=keystrokes,
        isStickyStart=bool(parsed.get("isStickyStart", False)),
    )


def decode_keystroke_data(raw) -> KeystrokeData:
    """Decode a JSON string, a pre-parsed compact array, or a legacy object.

    Compact v1/v2 shape: [version, text, stickyStart, keystrokesStr]
    Legacy:              {text, keystrokes, isStickyStart}
    """
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        parsed = json.loads(raw)
    else:
        parsed = raw

    if isinstance(parsed, dict):
        return _decode_legacy_dict(parsed)

    if not isinstance(parsed, list) or len(parsed) < 4:
        raise KeystrokeCodecError("Invalid compact format: expected 4-element array")

    version, raw_text, sticky_start, keystrokes_str = parsed[0], parsed[1], parsed[2], parsed[3]
    if version not in (1, 2):
        raise KeystrokeCodecError(f"Unknown keystroke codec version: {version}")

    text = unicodedata.normalize("NFC", raw_text.replace("\r\n", "\n"))

    if not keystrokes_str:
        return KeystrokeData(text=text, keystrokes=[], isStickyStart=bool(sticky_start))

    keystrokes: List[Keystroke] = []
    cumulative_time = 0
    expected_next_pos = 0
    completed_chars = 0
    input_val = ""

    chars = list(keystrokes_str)
    i = 0

    while i < len(chars):
        td_start = i
        while i < len(chars) and chars[i] in _DIGITS:
            i += 1
        if i >= len(chars):
            break
        if i == td_start:
            # No digits where expected — skip one char to advance and continue.
            i += 1
            continue
        time_delta = int("".join(chars[td_start:i]))
        cumulative_time += time_delta

        modifier: Optional[str] = None
        delete_modifier: Optional[str] = None
        if (
            i < len(chars)
            and chars[i] in _INSERT_MODIFIERS
            and i + 1 < len(chars)
            and chars[i + 1] in ("+", ">")
        ):
            modifier = chars[i]
            i += 1
        elif (
            i < len(chars)
            and chars[i] in _DELETE_MODIFIERS
            and i + 1 < len(chars)
            and chars[i + 1] in ("<", "-", "=")
        ):
            delete_modifier = chars[i]
            i += 1

        if i >= len(chars):
            break
        action_code = chars[i]
        i += 1

        action: Optional[KeystrokeAction] = None

        if action_code == "^":
            comp_pos = expected_next_pos
            if i < len(chars) and chars[i] in _DIGITS:
                j = i
                while j < len(chars) and chars[j] in _DIGITS:
                    j += 1
                if j < len(chars) and chars[j] == SEP_PARAM:
                    comp_pos = int("".join(chars[i:j]))
                    i = j + 1

            key_start = i
            while i < len(chars) and chars[i] != ":":
                i += 1
            key = "".join(chars[key_start:i])
            if i < len(chars):
                i += 1

            steps_start = i
            while i < len(chars) and chars[i] != ":":
                i += 1
            steps_str = "".join(chars[steps_start:i])
            if i < len(chars):
                i += 1

            times_start = i
            while i < len(chars) and chars[i] != SEP_KEYSTROKE:
                i += 1
            times_str = "".join(chars[times_start:i])

            steps = steps_str.split(SEP_PARAM) if steps_str else []
            if not steps:
                step_times: List[int] = []
            elif times_str:
                step_times = [0] + [int(x) for x in times_str.split(SEP_PARAM)]
            else:
                step_times = [0]

            action = KeystrokeComposition(i=comp_pos, key=key, steps=steps, stepTimes=step_times)
            input_val = input_val[:comp_pos] + key + input_val[comp_pos:]

        elif action_code == "+":
            key, i = _read_key_until_delimiter(chars, i)
            action = KeystrokeInsert(i=expected_next_pos, key=key, mod=modifier)
            input_val = input_val[:expected_next_pos] + key + input_val[expected_next_pos:]

        elif action_code == ">":
            pos_start = i
            while i < len(chars) and chars[i] != SEP_PARAM:
                i += 1
            pos = int("".join(chars[pos_start:i])) if i > pos_start else 0
            if i < len(chars):
                i += 1
            key, i = _read_key_until_delimiter(chars, i)
            action = KeystrokeInsert(i=pos, key=key, mod=modifier)
            input_val = input_val[:pos] + key + input_val[pos:]

        elif action_code == "<":
            d_start = expected_next_pos - 1
            action = KeystrokeDelete(dStart=d_start, dEnd=d_start + 1, mod=delete_modifier)
            if 0 <= d_start < len(input_val):
                input_val = input_val[:d_start] + input_val[d_start + 1:]

        elif action_code == "-":
            start_str_start = i
            while i < len(chars) and chars[i] in _DIGITS:
                i += 1
            d_start = int("".join(chars[start_str_start:i])) if i > start_str_start else 0
            if i < len(chars) and chars[i] == SEP_PARAM:
                i += 1
                end_start = i
                while i < len(chars) and chars[i] in _DIGITS:
                    i += 1
                d_end = int("".join(chars[end_start:i])) if i > end_start else d_start
            else:
                d_end = expected_next_pos
            action = KeystrokeDelete(dStart=d_start, dEnd=d_end, mod=delete_modifier)
            input_val = input_val[:d_start] + input_val[d_end:]

        elif action_code == "=":
            start_str_start = i
            while i < len(chars) and chars[i] in _DIGITS:
                i += 1
            r_start = int("".join(chars[start_str_start:i])) if i > start_str_start else 0
            if i < len(chars) and chars[i] == SEP_PARAM:
                i += 1  # skip first ','
            look = i
            while look < len(chars) and chars[look] in _DIGITS:
                look += 1
            if look < len(chars) and chars[look] == SEP_PARAM and look > i:
                end_start = i
                while i < len(chars) and chars[i] in _DIGITS:
                    i += 1
                r_end = int("".join(chars[end_start:i])) if i > end_start else r_start
                if i < len(chars):
                    i += 1
                key, i = _read_key_until_delimiter(chars, i)
            else:
                key, i = _read_key_until_delimiter(chars, i)
                r_end = expected_next_pos
            action = KeystrokeReplace(rStart=r_start, rEnd=r_end, key=key, mod=delete_modifier)
            input_val = input_val[:r_start] + key + input_val[r_end:]

        elif action_code == "~":
            pos_str_start = i
            if i < len(chars) and chars[i] == "-":
                i += 1
            while i < len(chars) and chars[i] in _DIGITS:
                i += 1
            r_start_raw = "".join(chars[pos_str_start:i])
            r_start = int(r_start_raw) if r_start_raw and r_start_raw != "-" else 0
            if r_start < 0:
                action = KeystrokeReplace(rStart=0, rEnd=0, key="", redundant=True)
            else:
                key = input_val[r_start] if 0 <= r_start < len(input_val) else ""
                action = KeystrokeReplace(
                    rStart=r_start, rEnd=r_start + 1, key=key, redundant=True
                )

        else:
            while i < len(chars) and chars[i] != SEP_KEYSTROKE:
                i += 1
            if i < len(chars) and chars[i] == SEP_KEYSTROKE:
                i += 1
            continue

        keystrokes.append(Keystroke(action=action, time=cumulative_time, timeDelta=time_delta))

        input_val, completed_chars = simulate_word_completion(input_val, text, completed_chars)
        expected_next_pos = len(input_val)

        if i < len(chars) and chars[i] == SEP_KEYSTROKE:
            i += 1

    return KeystrokeData(text=text, keystrokes=keystrokes, isStickyStart=bool(sticky_start))


def is_compact_format(data: str) -> bool:
    try:
        parsed = json.loads(data)
    except (ValueError, TypeError):
        return False
    return isinstance(parsed, list) and len(parsed) > 0 and parsed[0] in (1, 2)
