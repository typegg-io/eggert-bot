"""Keystroke codec decoder for compact format."""

import json
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

from utils.keystrokes import (
    KeystrokeData, Keystroke, KeystrokeInsert, KeystrokeDelete,
    KeystrokeReplace, KeystrokeComposition
)


def normalize_newlines(s: str) -> str:
    s = s.replace('⏎', '\n')
    s = s.replace('\r\n', '\n')
    return s


def find_word_break(s: str) -> int:
    for i, c in enumerate(s):
        if c in (' ', '\n', '⏎'):
            return i
    return -1


def simulate_word_completion(input_val: str, text: str, completed_chars: int) -> Tuple[str, int]:
    remaining_text = text[completed_chars:]
    if len(remaining_text) == 0:
        return input_val, completed_chars

    new_input_val = input_val
    new_completed_chars = completed_chars

    while len(new_input_val) > 0:
        remaining = text[new_completed_chars:]
        if len(remaining) == 0:
            break

        break_idx = find_word_break(remaining)
        if break_idx < 0:
            break

        word_end_idx = break_idx + 1
        word = remaining[:word_end_idx]

        if len(word) == 0:
            break

        normalized_input = normalize_newlines(new_input_val)
        normalized_word = normalize_newlines(word)

        if len(normalized_input) >= len(normalized_word):
            matches = normalized_input[:len(normalized_word)] == normalized_word
            if matches:
                slice_len = len(normalized_word)
                new_input_val = new_input_val[slice_len:] if slice_len <= len(new_input_val) else ""
                new_completed_chars += len(word)
            else:
                break
        else:
            break

    return new_input_val, new_completed_chars


def insert_at(s: str, pos: int, insert: str) -> str:
    if pos < 0:
        pos = 0
    if pos > len(s):
        pos = len(s)
    return s[:pos] + insert + s[pos:]


def delete_range(s: str, start: int, end: int) -> str:
    if start < 0:
        start = 0
    if end > len(s):
        end = len(s)
    if start >= end:
        return s
    return s[:start] + s[end:]


def replace_range(s: str, start: int, end: int, replacement: str) -> str:
    if start < 0:
        start = 0
    if end > len(s):
        end = len(s)
    return s[:start] + replacement + s[end:]


def read_key_until_delimiter(runes: str, i: int) -> Tuple[str, int]:
    if i >= len(runes):
        return "", i
    if runes[i] == '|':
        return "|", i + 1
    start = i
    while i < len(runes) and runes[i] != '|':
        i += 1
    return runes[start:i], i


def decode_keystroke_data(encoded: bytes) -> KeystrokeData:
    """Decode keystroke data from JSON (compact or legacy format)."""
    raw = json.loads(encoded)

    # Legacy format (dict with text and keystrokes)
    if isinstance(raw, dict):
        keystrokes = []
        for ks in raw.get("keystrokes", []):
            action = ks["action"]
            if "i" in action:
                action_obj = KeystrokeInsert(i=action["i"], key=action["key"])
            elif "dStart" in action:
                action_obj = KeystrokeDelete(dStart=action["dStart"], dEnd=action["dEnd"])
            elif "rStart" in action:
                action_obj = KeystrokeReplace(
                    rStart=action["rStart"],
                    rEnd=action["rEnd"],
                    key=action.get("key", ""),
                    redundant=action.get("redundant")
                )
            else:
                continue
            keystrokes.append(Keystroke(
                action=action_obj,
                time=ks["time"],
                timeDelta=ks["timeDelta"]
            ))
        return KeystrokeData(
            text=raw["text"],
            keystrokes=keystrokes,
            isStickyStart=raw.get("isStickyStart", False)
        )

    # Compact format [version, text, stickyStart, keystrokesStr]
    if not isinstance(raw, list) or len(raw) < 4:
        raise ValueError("Invalid compact format")

    version = raw[0]
    if version not in (1, 2):
        raise ValueError(f"Unknown codec version: {version}")

    text = raw[1].replace('\r\n', '\n')
    sticky_start = raw[2] != 0
    keystrokes_str = raw[3]

    if not keystrokes_str:
        return KeystrokeData(text=text, keystrokes=[], isStickyStart=sticky_start)

    keystrokes = []
    cumulative_time = 0
    expected_next_pos = 0
    input_val = ""
    completed_chars = 0

    i = 0
    runes = keystrokes_str

    while i < len(runes):
        # Read timeDelta
        time_delta_str = ""
        while i < len(runes) and runes[i].isdigit():
            time_delta_str += runes[i]
            i += 1

        if i >= len(runes):
            break

        try:
            time_delta = int(time_delta_str)
        except ValueError:
            while i < len(runes) and not runes[i].isdigit():
                i += 1
            continue

        cumulative_time += time_delta

        # Check for modifier prefix
        modifier = ""
        delete_modifier = ""
        if i < len(runes) and i + 1 < len(runes):
            potential_mod = runes[i]
            next_char = runes[i + 1]
            if potential_mod in ('L', 'R', 'S', 'C', 'V') and next_char in ('+', '>'):
                modifier = potential_mod
                i += 1
            elif potential_mod in ('X', 'M') and next_char in ('<', '-', '='):
                delete_modifier = potential_mod
                i += 1

        action_code = runes[i]
        i += 1

        action = None

        if action_code == '^':
            # Composition
            key_builder = ""
            while i < len(runes) and runes[i] != ':':
                key_builder += runes[i]
                i += 1
            i += 1  # skip ':'

            steps_str = ""
            while i < len(runes) and runes[i] != ':':
                steps_str += runes[i]
                i += 1
            i += 1  # skip ':'

            times_str = ""
            while i < len(runes) and runes[i] != '|':
                times_str += runes[i]
                i += 1

            steps = steps_str.split(',') if steps_str else []
            step_times = []
            if times_str:
                step_times = [0] + [int(t) for t in times_str.split(',') if t]
            elif steps:
                step_times = [0]

            action = KeystrokeComposition(i=expected_next_pos, key=key_builder, steps=steps, stepTimes=step_times)
            input_val = insert_at(input_val, expected_next_pos, key_builder)

        elif action_code == '+':
            if i >= len(runes):
                break
            key, i = read_key_until_delimiter(runes, i)
            action = KeystrokeInsert(i=expected_next_pos, key=key)
            input_val = insert_at(input_val, expected_next_pos, key)

        elif action_code == '>':
            pos_str = ""
            while i < len(runes) and runes[i] != ',':
                pos_str += runes[i]
                i += 1
            i += 1  # skip ','
            pos = int(pos_str)
            if i >= len(runes):
                break
            key, i = read_key_until_delimiter(runes, i)
            action = KeystrokeInsert(i=pos, key=key)
            input_val = insert_at(input_val, pos, key)

        elif action_code == '<':
            d_start = expected_next_pos - 1
            if d_start < 0:
                action = KeystrokeDelete(dStart=0, dEnd=0)
            else:
                action = KeystrokeDelete(dStart=d_start, dEnd=d_start + 1)
                input_val = delete_range(input_val, d_start, d_start + 1)

        elif action_code == '-':
            start_str = ""
            while i < len(runes) and runes[i].isdigit():
                start_str += runes[i]
                i += 1
            d_start = int(start_str)

            if i < len(runes) and runes[i] == ',':
                i += 1
                end_str = ""
                while i < len(runes) and runes[i].isdigit():
                    end_str += runes[i]
                    i += 1
                d_end = int(end_str)
            else:
                d_end = expected_next_pos

            action = KeystrokeDelete(dStart=d_start, dEnd=d_end)
            input_val = delete_range(input_val, d_start, d_end)

        elif action_code == '=':
            start_str = ""
            while i < len(runes) and runes[i].isdigit():
                start_str += runes[i]
                i += 1
            i += 1  # skip ','
            r_start = int(start_str)

            # Check for full format
            look_ahead = i
            while look_ahead < len(runes) and runes[look_ahead].isdigit():
                look_ahead += 1

            if look_ahead > i and look_ahead < len(runes) and runes[look_ahead] == ',':
                end_str = ""
                while i < len(runes) and runes[i].isdigit():
                    end_str += runes[i]
                    i += 1
                i += 1  # skip ','
                if i >= len(runes):
                    break
                key, i = read_key_until_delimiter(runes, i)
                r_end = int(end_str)
            else:
                if i >= len(runes):
                    break
                key, i = read_key_until_delimiter(runes, i)
                r_end = expected_next_pos

            action = KeystrokeReplace(rStart=r_start, rEnd=r_end, key=key)
            input_val = replace_range(input_val, r_start, r_end, key)

        elif action_code == '~':
            pos_str = ""
            if i < len(runes) and runes[i] == '-':
                pos_str += '-'
                i += 1
            while i < len(runes) and runes[i].isdigit():
                pos_str += runes[i]
                i += 1
            r_start = int(pos_str)
            if r_start < 0:
                action = KeystrokeReplace(rStart=0, rEnd=0, key="", redundant=True)
            else:
                key = input_val[r_start] if r_start < len(input_val) else ""
                action = KeystrokeReplace(rStart=r_start, rEnd=r_start + 1, key=key, redundant=True)

        else:
            continue

        keystrokes.append(Keystroke(
            action=action,
            time=cumulative_time,
            timeDelta=time_delta
        ))

        input_val, completed_chars = simulate_word_completion(input_val, text, completed_chars)
        expected_next_pos = len(input_val)

        if i < len(runes) and runes[i] == '|':
            i += 1

    return KeystrokeData(text=text, keystrokes=keystrokes, isStickyStart=sticky_start)
