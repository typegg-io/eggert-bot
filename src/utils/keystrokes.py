"""Decodes a keystroke replay into per-character timing data, a per-keystroke WPM
graph, per-word WPM graph, typos, and overall WPM / raw WPM / accuracy / duration.

Entry points:
  - get_keystroke_data(raw, is_multiplayer=False, start_time=0) — decode + process
  - process_keystroke_data(KeystrokeData, ...) — process an already-decoded replay
  - get_keystroke_wpm(delays, adjusted=True) — running WPM from a list of delays
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from utils.errors import InvalidKeystrokeData
from utils.stats import calculate_wpm
from utils.keystroke_codec import (
    Keystroke,
    KeystrokeComposition,
    KeystrokeData,
    KeystrokeDelete,
    KeystrokeInsert,
    KeystrokeReplace,
    decode_keystroke_data,
)

TRANSPOSITION_THRESHOLD_MS = 7
ATTRIBUTION_WINDOW = 7


@dataclass
class Typo:
    charIndex: int
    wordIndex: int
    typo: str
    time: int
    timeToReact: int = 0
    recoveryDelay: Optional[int] = None
    correctionTime: int = 0
    editDistance: int = 0


@dataclass
class GraphDataPoint:
    charIndex: int
    wordIndex: int
    initialKeystrokeId: int = -1
    wpm: Optional[float] = None
    raw: Optional[float] = None
    time: int = 0
    typos: List[Typo] = field(default_factory=list)


@dataclass
class WordGraphDataPoint:
    time: int
    wpm: float = 0.0
    raw: float = 0.0
    typos: List[Typo] = field(default_factory=list)


@dataclass
class ProcessResult:
    keystrokesWpmGraphData: List[GraphDataPoint] = field(default_factory=list)
    wordWpmGraphData: List[WordGraphDataPoint] = field(default_factory=list)
    rawCharacterTimes: List[float] = field(default_factory=list)
    wpmCharacterTimes: List[float] = field(default_factory=list)
    typos: List[Typo] = field(default_factory=list)
    keystrokeWpm: List[float] = field(default_factory=list)
    keystrokeRawWpm: List[float] = field(default_factory=list)
    raw_wpm: float = 0.0
    wpm: float = 0.0
    accuracy: float = 0.0
    duration: int = 0


def split_words(text: str) -> List[str]:
    """Split text into words, preserving trailing space on each (except the last,
    or when a word ends with the ⏎ newline glyph)."""
    out: List[str] = []
    runes = list(text)
    for i, ch in enumerate(runes):
        out.append(ch)
        if ch == "⏎" and (i + 1 >= len(runes) or runes[i + 1] != " "):
            out.append(" ")
    text = "".join(out)

    text = text.replace("\r\n", "⏎ ").replace("\n", "⏎ ")
    parts = [w for w in text.split(" ") if w != ""]
    for i in range(len(parts) - 1):
        if not parts[i].endswith("⏎"):
            parts[i] = parts[i] + " "
    return parts


def _edit_distance(s: str, t: str) -> int:
    """Levenshtein edit distance."""
    m, n = len(s), len(t)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            if s[i - 1] == t[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev, curr = curr, prev
    return prev[n]


def _find_first_non_matching(p: str, q: str) -> int:
    min_len = min(len(p), len(q))
    for i in range(min_len):
        if p[i] != q[i]:
            return i
    if len(p) != len(q):
        return min_len
    return -1


def _is_combining_mark(ch: str) -> bool:
    return bool(ch) and unicodedata.category(ch[0]).startswith("M")


def _build_grapheme_mapping(text: str) -> Tuple[List[int], List[int], int]:
    """Return (cp_to_grapheme, grapheme_to_cp, grapheme_count).

    Combining marks map to the same grapheme index as their preceding base char.
    """
    cp_to_g: List[int] = []
    g_to_cp: List[int] = []
    count = 0
    for i, ch in enumerate(text):
        if i > 0 and _is_combining_mark(ch):
            cp_to_g.append(count - 1)
        else:
            g_to_cp.append(i)
            cp_to_g.append(count)
            count += 1
    return cp_to_g, g_to_cp, count


def _is_partial_surrogate(input_char: str, expected_char: str) -> bool:
    """Input is a lone high surrogate / U+FFFD standing in for an astral plane char."""
    if not input_char or not expected_char:
        return False
    if len(input_char) != 1:
        return False
    code = ord(input_char)
    is_high_or_fffd = (0xD800 <= code <= 0xDBFF) or code == 0xFFFD
    if not is_high_or_fffd:
        return False
    expected_cp = ord(expected_char[0])
    if expected_cp <= 0xFFFF:
        return False
    if code == 0xFFFD:
        return True
    return ord(expected_char[0]) == code


def _is_grapheme_prefix_correct(input_val: str, word: str) -> bool:
    """True iff input_val is a valid grapheme-prefix of word, allowing a final
    partial grapheme (e.g. 'e' while the user is still typing 'ė' via a dead-key
    layout — combining marks land after the base letter).
    """
    nfd_input = unicodedata.normalize("NFD", input_val)
    nfd_word = unicodedata.normalize("NFD", word)
    _, i_gtocp, i_gcount = _build_grapheme_mapping(nfd_input)
    _, w_gtocp, w_gcount = _build_grapheme_mapping(nfd_word)
    i_len_total = len(nfd_input)
    w_len_total = len(nfd_word)
    max_g = min(i_gcount, w_gcount)

    for gi in range(max_g):
        i_start = i_gtocp[gi]
        i_end = i_gtocp[gi + 1] if gi + 1 < i_gcount else i_len_total
        w_start = w_gtocp[gi]
        w_end = w_gtocp[gi + 1] if gi + 1 < w_gcount else w_len_total
        i_len = i_end - i_start
        w_len = w_end - w_start

        if i_len > w_len:
            return False

        i_base = nfd_input[i_start]
        w_base = nfd_word[w_start]
        if i_base != w_base:
            # d↔đ, D↔Đ (Vietnamese Telex dd→đ)
            if not (
                (i_base == "d" and w_base == "đ")
                or (i_base == "D" and w_base == "Đ")
            ):
                if not _is_partial_surrogate(i_base, w_base):
                    return False
                if gi < i_gcount - 1:
                    return False

        if i_len < w_len:
            if i_end > i_start + 1:
                word_marks = nfd_word[w_start + 1:w_end]
                for j in range(i_start + 1, i_end):
                    if nfd_input[j] not in word_marks:
                        return False
        else:
            for j in range(1, i_len):
                i_ch = nfd_input[i_start + j]
                w_ch = nfd_word[w_start + j]
                if i_ch != w_ch:
                    if not _is_partial_surrogate(i_ch, w_ch):
                        return False
                    if j < i_len - 1 or gi < i_gcount - 1:
                        return False
    return True


def _normalize_enter(ch: str) -> str:
    if ch in ("\n", "\r"):
        return "⏎"
    return ch


def _action_key(action) -> str:
    if isinstance(action, (KeystrokeInsert, KeystrokeReplace, KeystrokeComposition)):
        return action.key
    return ""


class _Processor:
    """Keystroke replay processor. Each keystroke goes through three stages:

      - _dispatch_action → per-action handler (Insert / Composition / Replace / Delete)
      - _update_accuracy_bookkeeping → typo flags, combo counter, penalties
      - _process_word_completions → flushes completed words to the graph

    _finalize runs once at the end to compute overall WPM / accuracy and enforce
    the ranked burst-WPM cap.
    """

    def __init__(
        self,
        keystroke_data: KeystrokeData,
        is_multiplayer: bool,
        reaction_time: float,
        is_ranked: bool,
    ):
        self.keystrokes = keystroke_data.keystrokes
        self.text = unicodedata.normalize("NFC", keystroke_data.text.replace("\r\n", "\n"))
        self.text_cps = list(self.text)
        self.cp_to_grapheme, _, self.grapheme_count = _build_grapheme_mapping(self.text)
        self.words = split_words(self.text)
        self.is_multiplayer = is_multiplayer
        self.reaction_time = reaction_time
        self.is_ranked = is_ranked

        self.raw_character_times: List[float] = []
        self.wpm_character_times: List[float] = []
        self.raw_word_times: List[float] = []

        self.char_pool: Dict[str, List[Tuple[int, int]]] = {}
        self.fat_finger_times: Dict[int, int] = {}

        self.prev_insert_key: Optional[str] = None
        self.prev_insert_abs_pos: int = -1
        self.prev_insert_keystroke_id: int = -1
        self.prev_was_insert = False

        self.tracking_sequence_pos = -1

        self.positions_typed_correctly: set[int] = set()
        self.attribution_started = False

        self.position_keystrokes: Dict[int, List[Tuple[int, int]]] = {}
        self.post_correction_positions: set[int] = set()
        self.correction_ks_ids: set[int] = set()
        self.pending_post_delete_positions: set[int] = set()

        self.input_val_contributors: List[int] = []
        self.input_val_delays: List[List[int]] = []
        self.pending_delays: List[int] = []

        self.initial_keystroke_assigned = [False] * len(self.text_cps)
        self.char_initial_keystroke_ids = [-1] * len(self.text_cps)

        self.word_wpm_graph_data: List[WordGraphDataPoint] = []
        self.initial_typo: Optional[Dict[str, Any]] = None
        self.word_typos: List[Typo] = []
        self.char_typos: List[Typo] = []
        self.last_word_completion_time = 0

        self.keystrokes_wpm_graph_data: List[GraphDataPoint] = []
        self.initial_keystroke_input_states: Dict[int, str] = {}

        self.correct_chars = 0
        self.corrective = 0
        self.destructive = 0
        self.penalties = 0
        self.combo_counter = 0
        self.longest_combo = 0

        self.input_val = ""
        self.word_index = 0
        self.prev_input = ""
        self.prev_has_typo = False

        self.wpm_running_total = 0.0
        self.raw_running_total = 0.0
        self.raw_word_times_total = 0.0
        self.total_chars_before_word = 0

        self.global_used_raw_ids: set[int] = set()
        self.global_used_actual_ids: set[int] = set()

        self.is_clean_solo_start = self._detect_clean_solo_start()

    def _detect_clean_solo_start(self) -> bool:
        if not self.keystrokes:
            return False
        first_key = ""
        if isinstance(
            self.keystrokes[0].action,
            (KeystrokeInsert, KeystrokeReplace, KeystrokeComposition),
        ):
            first_key = self.keystrokes[0].action.key
        first_is_partial_surrogate = bool(first_key) and (
            ord(first_key[0]) == 0xFFFD or 0xD800 <= ord(first_key[0]) <= 0xDBFF
        )
        return (
            not self.is_multiplayer
            and self.keystrokes[0].timeDelta == 0
            and not isinstance(self.keystrokes[0].action, KeystrokeComposition)
            and not first_is_partial_surrogate
        )

    def run(self) -> ProcessResult:
        for ks_id, ks in enumerate(self.keystrokes):
            self._dispatch_action(ks_id, ks)
            has_typo = self._update_accuracy_bookkeeping(ks)
            self._process_word_completions(ks)
            self.prev_input = self.input_val
            self.prev_has_typo = has_typo
        return self._finalize()

    def _curr_word(self) -> str:
        return self.words[self.word_index] if self.word_index < len(self.words) else ""

    def _add_to_char_pool(self, char: str, keystroke_id: int, typed_at_pos: int) -> None:
        effective_char = char
        if char and ord(char[0]) == 0xFFFD and 0 <= typed_at_pos < len(self.text_cps):
            expected = self.text_cps[typed_at_pos]
            if ord(expected[0]) > 0xFFFF:
                effective_char = expected
        normalized = _normalize_enter(effective_char).lower() if effective_char else ""
        lst = self.char_pool.get(normalized)
        if lst is None:
            self.char_pool[normalized] = [(keystroke_id, typed_at_pos)]
        else:
            lst.append((keystroke_id, typed_at_pos))

    def _add_to_position_keystrokes(self, abs_pos: int, keystroke_id: int, time_delta: int) -> None:
        lst = self.position_keystrokes.get(abs_pos)
        if lst is None:
            self.position_keystrokes[abs_pos] = [(keystroke_id, time_delta)]
        else:
            lst.append((keystroke_id, time_delta))

    def _track_correct_position(self, abs_pos: int) -> None:
        if abs_pos in self.positions_typed_correctly:
            self.attribution_started = True
        self.positions_typed_correctly.add(abs_pos)

    def _find_char_in_text(self, ch: str, start_from: int = 0) -> int:
        norm = _normalize_enter(ch)
        for idx in range(start_from, len(self.text_cps)):
            if _normalize_enter(self.text_cps[idx]) == norm:
                return idx
        return -1

    def _flush_initial_typo(self, now_ms: int, pos_guard: Optional[int] = None) -> None:
        if not self.prev_has_typo or self.initial_typo is None:
            return
        if pos_guard is not None and pos_guard >= len(self.input_val):
            return
        self.word_typos.append(
            Typo(
                charIndex=self.initial_typo["charIndex"],
                wordIndex=self.initial_typo["wordIndex"],
                typo=self.input_val,
                time=self.initial_typo["time"],
                timeToReact=now_ms - self.initial_typo["time"],
            )
        )
        self.initial_typo = None

    def _record_initial_keystroke(self, abs_position: int, ks_id: int) -> None:
        if self.prev_has_typo:
            return
        if not (0 <= abs_position < len(self.initial_keystroke_assigned)):
            return
        if self.initial_keystroke_assigned[abs_position]:
            return
        self.initial_keystroke_assigned[abs_position] = True
        self.char_initial_keystroke_ids[abs_position] = ks_id
        if abs_position > 0:
            self.initial_keystroke_input_states[abs_position - 1] = self.prev_input

    def _splice_contributors(self, i_clamped: int, ks_id: int, key_cp_len: int) -> None:
        delays = list(self.pending_delays) if self.pending_delays else []
        if i_clamped >= len(self.input_val_contributors):
            for cp in range(key_cp_len):
                self.input_val_contributors.append(ks_id)
                self.input_val_delays.append(delays if cp == 0 else [])
        else:
            contribs = [ks_id] * key_cp_len
            delay_entries = [delays if cp == 0 else [] for cp in range(key_cp_len)]
            self.input_val_contributors[i_clamped:i_clamped] = contribs
            self.input_val_delays[i_clamped:i_clamped] = delay_entries
        self.pending_delays = []

    def _dispatch_action(self, ks_id: int, ks: Keystroke) -> None:
        action = ks.action
        if isinstance(action, KeystrokeInsert):
            self._handle_insert(ks_id, ks, action)
        elif isinstance(action, KeystrokeComposition):
            self._handle_composition(ks_id, ks, action)
        elif isinstance(action, KeystrokeReplace):
            self._handle_replace(ks_id, ks, action)
        elif isinstance(action, KeystrokeDelete):
            self._handle_delete(ks_id, ks, action)

    def _handle_insert(self, ks_id: int, ks: Keystroke, ins: KeystrokeInsert) -> None:
        time_ms = ks.time
        time_delta = ks.timeDelta
        curr_word = self._curr_word()
        self._flush_initial_typo(time_ms, pos_guard=ins.i)

        # Older replay format encodes i as a full-text index, not a word-relative one.
        effective_i = ins.i
        if ins.i > len(self.input_val) and self.total_chars_before_word > 0:
            per_word = ins.i - self.total_chars_before_word
            if 0 <= per_word <= len(curr_word):
                effective_i = per_word

        i_clamped = max(0, min(effective_i, len(self.input_val)))
        key_cps = list(ins.key)
        key_cp_len = len(key_cps)

        self.input_val = self.input_val[:i_clamped] + ins.key + self.input_val[i_clamped:]
        self._splice_contributors(i_clamped, ks_id, key_cp_len)

        abs_pos = self.total_chars_before_word + i_clamped
        if abs_pos in self.pending_post_delete_positions:
            self.correction_ks_ids.add(ks_id)
            self.pending_post_delete_positions.discard(abs_pos)

        self._add_to_position_keystrokes(abs_pos, ks_id, time_delta)

        first_cp = key_cps[0] if key_cps else ""
        normalized_key = _normalize_enter(first_cp)
        expected_char = _normalize_enter(self.text_cps[abs_pos]) if 0 <= abs_pos < len(self.text_cps) else ""
        exact_match = normalized_key == expected_char or _is_partial_surrogate(normalized_key, expected_char)
        case_insensitive_match = (
            not exact_match
            and bool(normalized_key)
            and normalized_key.lower() == expected_char.lower()
        )

        if 0 <= abs_pos < len(self.text_cps) and (exact_match or case_insensitive_match):
            for cp in range(key_cp_len):
                pos = abs_pos + cp
                if exact_match or cp == 0:
                    self._track_correct_position(pos)
                self._add_to_char_pool(key_cps[cp], ks_id, pos)
            self.tracking_sequence_pos = abs_pos + key_cp_len
        elif (
            0 <= self.tracking_sequence_pos < len(self.text_cps)
            and (
                normalized_key == _normalize_enter(self.text_cps[self.tracking_sequence_pos])
                or normalized_key.lower() == _normalize_enter(self.text_cps[self.tracking_sequence_pos]).lower()
            )
        ):
            for cp in range(key_cp_len):
                pos = self.tracking_sequence_pos + cp
                if normalized_key == _normalize_enter(self.text_cps[self.tracking_sequence_pos]) or cp == 0:
                    self._track_correct_position(pos)
                self._add_to_char_pool(key_cps[cp], ks_id, pos)
            self.tracking_sequence_pos += key_cp_len
        else:
            match_pos = self._find_char_in_text(first_cp)
            self.tracking_sequence_pos = match_pos + key_cp_len if match_pos >= 0 else -1

        self._detect_fat_finger(ks_id, time_delta, normalized_key)

        self.prev_insert_key = ins.key
        self.prev_insert_abs_pos = abs_pos
        self.prev_insert_keystroke_id = ks_id
        self.prev_was_insert = True

        self._record_initial_keystroke(self.total_chars_before_word + ins.i, ks_id)

    def _handle_composition(self, ks_id: int, ks: Keystroke, comp: KeystrokeComposition) -> None:
        # IME composition — insert-like, but never participates in fat-finger detection
        # and never updates prev_insert tracking.
        time_ms = ks.time
        time_delta = ks.timeDelta
        curr_word = self._curr_word()
        self._flush_initial_typo(time_ms, pos_guard=comp.i)

        effective_i = comp.i
        if comp.i > len(self.input_val) and self.total_chars_before_word > 0:
            per_word = comp.i - self.total_chars_before_word
            if 0 <= per_word <= len(curr_word):
                effective_i = per_word

        i_clamped = max(0, min(effective_i, len(self.input_val)))
        key_cps = list(comp.key)
        key_cp_len = len(key_cps)

        self.input_val = self.input_val[:i_clamped] + comp.key + self.input_val[i_clamped:]
        self._splice_contributors(i_clamped, ks_id, key_cp_len)

        abs_pos = self.total_chars_before_word + i_clamped
        self.pending_post_delete_positions.discard(abs_pos)

        self._add_to_position_keystrokes(abs_pos, ks_id, time_delta)

        first_cp = key_cps[0] if key_cps else ""
        normalized_key = _normalize_enter(first_cp)
        expected_char = _normalize_enter(self.text_cps[abs_pos]) if 0 <= abs_pos < len(self.text_cps) else ""
        exact_match = normalized_key == expected_char or _is_partial_surrogate(normalized_key, expected_char)

        if exact_match:
            self._track_correct_position(abs_pos)
            self._add_to_char_pool(first_cp, ks_id, abs_pos)
            self.tracking_sequence_pos = abs_pos + 1
        elif (
            0 <= self.tracking_sequence_pos < len(self.text_cps)
            and normalized_key.lower() == _normalize_enter(self.text_cps[self.tracking_sequence_pos]).lower()
        ):
            self._track_correct_position(self.tracking_sequence_pos)
            self._add_to_char_pool(first_cp, ks_id, self.tracking_sequence_pos)
            self.tracking_sequence_pos += 1
        else:
            match_pos = self._find_char_in_text(first_cp)
            self.tracking_sequence_pos = match_pos + 1 if match_pos >= 0 else -1

        self._record_initial_keystroke(self.total_chars_before_word + comp.i, ks_id)

    def _handle_replace(self, ks_id: int, ks: Keystroke, rep: KeystrokeReplace) -> None:
        time_ms = ks.time
        time_delta = ks.timeDelta
        curr_word = self._curr_word()
        self._flush_initial_typo(time_ms)

        effective_r_start = rep.rStart
        effective_r_end = rep.rEnd
        if rep.rStart > len(self.input_val) and self.total_chars_before_word > 0:
            effective_r_start = rep.rStart - self.total_chars_before_word
            effective_r_end = rep.rEnd - self.total_chars_before_word

        old_char = (
            self.input_val[effective_r_start]
            if 0 <= effective_r_start < len(self.input_val)
            else ""
        )
        is_composition = (
            not rep.redundant
            and old_char
            and rep.key
            and old_char != rep.key
            and unicodedata.normalize("NFD", rep.key).startswith(
                unicodedata.normalize("NFD", old_char)
            )
        )
        composition_extra_time = 0

        if rep.redundant:
            self.destructive += 1
        elif not is_composition:
            r_loop_start = max(0, min(effective_r_start, len(self.input_val)))
            r_loop_end = max(0, min(effective_r_end, len(self.input_val)))
            for idx in range(r_loop_start, r_loop_end):
                deleted_char = self.input_val[idx] if idx < len(self.input_val) else ""
                if not deleted_char:
                    continue
                curr_char = curr_word[idx] if idx < len(curr_word) else ""
                if not curr_char or deleted_char != curr_char:
                    self.corrective += 1
                else:
                    self.destructive += 1

            inserted_char = rep.key
            replace_index = effective_r_start
            curr_word_cps = list(curr_word)
            if 0 <= replace_index < len(curr_word_cps):
                if inserted_char and inserted_char == curr_word_cps[replace_index]:
                    self.corrective += 1
                else:
                    self.destructive += 1
            else:
                self.destructive += 1

        input_cp_len = len(self.input_val)
        r_start = max(0, min(effective_r_start, input_cp_len))
        r_end = max(0, min(effective_r_end, input_cp_len))

        if rep.redundant:
            if r_start < len(self.input_val_delays):
                self.input_val_delays[r_start].append(ks_id)
            else:
                self.pending_delays.append(ks_id)

        if (
            r_start <= r_end
            and r_start >= 0
            and r_end <= input_cp_len
            and not (rep.redundant and r_start == r_end)
        ):
            self.input_val = self.input_val[:r_start] + rep.key + self.input_val[r_end:]

            if not rep.redundant:
                replaced_contributors = self.input_val_contributors[r_start:r_end]
                if is_composition:
                    composition_extra_time = sum(
                        self.keystrokes[c].timeDelta for c in replaced_contributors if c >= 0
                    )
                replaced_delays = self.input_val_delays[r_start:r_end]

                preserved_ids: List[int] = []
                for cid in replaced_contributors:
                    if cid >= 0:
                        preserved_ids.append(cid)
                for d_arr in replaced_delays:
                    preserved_ids.extend(d_arr)

                r_key_cp_count = len(rep.key)
                r_contribs = [ks_id] * r_key_cp_count
                r_delay_entries = [preserved_ids if cp == 0 else [] for cp in range(r_key_cp_count)]
                self.input_val_contributors[r_start:r_end] = r_contribs
                self.input_val_delays[r_start:r_end] = r_delay_entries

            abs_pos = self.total_chars_before_word + r_start
            self._add_to_position_keystrokes(abs_pos, ks_id, time_delta + composition_extra_time)

            if (
                not rep.redundant
                and not is_composition
                and 0 <= abs_pos < len(self.text_cps)
            ):
                self.post_correction_positions.add(abs_pos)
                self.correction_ks_ids.add(ks_id)

            replace_cps = list(rep.key)
            normalized_replace_key = _normalize_enter(replace_cps[0]) if replace_cps else ""
            expected_at_pos = _normalize_enter(self.text_cps[abs_pos]) if 0 <= abs_pos < len(self.text_cps) else ""
            if 0 <= abs_pos < len(self.text_cps) and (
                normalized_replace_key == expected_at_pos
                or _is_partial_surrogate(normalized_replace_key, expected_at_pos)
            ):
                for cp in range(len(replace_cps)):
                    self._track_correct_position(abs_pos + cp)
                    self._add_to_char_pool(replace_cps[cp], ks_id, abs_pos + cp)
                self.tracking_sequence_pos = abs_pos + len(replace_cps)
            elif (
                0 <= self.tracking_sequence_pos < len(self.text_cps)
                and (
                    normalized_replace_key == _normalize_enter(self.text_cps[self.tracking_sequence_pos])
                    or _is_partial_surrogate(
                        normalized_replace_key,
                        _normalize_enter(self.text_cps[self.tracking_sequence_pos]),
                    )
                )
            ):
                for cp in range(len(replace_cps)):
                    self._track_correct_position(self.tracking_sequence_pos + cp)
                    self._add_to_char_pool(replace_cps[cp], ks_id, self.tracking_sequence_pos + cp)
                self.tracking_sequence_pos += len(replace_cps)
            else:
                match_pos = self._find_char_in_text(replace_cps[0]) if replace_cps else -1
                self.tracking_sequence_pos = match_pos + len(replace_cps) if match_pos >= 0 else -1

            self._detect_fat_finger(ks_id, time_delta, normalized_replace_key)

            self.prev_insert_key = rep.key
            self.prev_insert_abs_pos = abs_pos
            self.prev_insert_keystroke_id = ks_id
            self.prev_was_insert = True

        self._record_initial_keystroke(self.total_chars_before_word + rep.rStart, ks_id)

    def _handle_delete(self, ks_id: int, ks: Keystroke, d: KeystrokeDelete) -> None:
        time_ms = ks.time
        curr_word = self._curr_word()
        self._flush_initial_typo(time_ms)

        effective_d_start = d.dStart
        effective_d_end = d.dEnd
        if d.dStart > len(self.input_val) and self.total_chars_before_word > 0:
            effective_d_start = d.dStart - self.total_chars_before_word
            effective_d_end = d.dEnd - self.total_chars_before_word

        input_cp_len = len(self.input_val)
        d_start = max(0, min(effective_d_start, input_cp_len))
        d_end = max(0, min(effective_d_end, input_cp_len))
        if d_start > d_end:
            d_start, d_end = d_end, d_start

        input_cps = list(self.input_val)
        curr_word_cps = list(curr_word)
        for idx in range(d_start, d_end):
            deleted_char = input_cps[idx] if idx < len(input_cps) else None
            expected_char = curr_word_cps[idx] if idx < len(curr_word_cps) else None
            if not deleted_char:
                continue
            if not expected_char or deleted_char != expected_char:
                self.corrective += 1
            else:
                self.destructive += 1

        self.input_val = self.input_val[:d_start] + self.input_val[d_end:]

        deleted_contributors = self.input_val_contributors[d_start:d_end]
        deleted_delays = self.input_val_delays[d_start:d_end]
        preserved_ids: List[int] = []
        for cid in deleted_contributors:
            if cid >= 0:
                preserved_ids.append(cid)
        for d_arr in deleted_delays:
            preserved_ids.extend(d_arr)

        del self.input_val_contributors[d_start:d_end]
        del self.input_val_delays[d_start:d_end]

        if d_start < len(self.input_val_delays):
            self.input_val_delays[d_start].append(ks_id)
            self.input_val_delays[d_start].extend(preserved_ids)
        else:
            self.pending_delays.append(ks_id)
            self.pending_delays.extend(preserved_ids)

        self.tracking_sequence_pos = -1
        self.prev_was_insert = False

        tail_pos_after_delete = self.total_chars_before_word + d_start
        if 0 <= tail_pos_after_delete < len(self.text_cps):
            self.post_correction_positions.add(tail_pos_after_delete)
            self.pending_post_delete_positions.add(tail_pos_after_delete)

    def _detect_fat_finger(self, ks_id: int, time_delta: int, normalized_key: str) -> None:
        if not (
            self.prev_was_insert
            and self.prev_insert_key is not None
            and self.prev_insert_abs_pos >= 0
            and self.prev_insert_keystroke_id >= 0
            and time_delta <= TRANSPOSITION_THRESHOLD_MS
        ):
            return
        if not (
            0 <= self.prev_insert_abs_pos < len(self.text_cps)
            and _normalize_enter(self.prev_insert_key[0] if self.prev_insert_key else "")
            != _normalize_enter(self.text_cps[self.prev_insert_abs_pos])
            and normalized_key == _normalize_enter(self.text_cps[self.prev_insert_abs_pos])
        ):
            return
        self._track_correct_position(self.prev_insert_abs_pos)
        self._add_to_char_pool(self.text_cps[self.prev_insert_abs_pos], ks_id, self.prev_insert_abs_pos)
        prev_time = self.fat_finger_times.get(
            self.prev_insert_keystroke_id,
            self.keystrokes[self.prev_insert_keystroke_id].timeDelta,
        )
        self.fat_finger_times[ks_id] = prev_time + time_delta

    def _update_accuracy_bookkeeping(self, ks: Keystroke) -> bool:
        action = ks.action
        time_ms = ks.time
        time_delta = ks.timeDelta
        curr_word = self._curr_word()

        has_typo = False
        if curr_word and self.input_val:
            has_typo = not _is_grapheme_prefix_correct(self.input_val, curr_word)

        is_insertive = isinstance(action, (KeystrokeInsert, KeystrokeReplace, KeystrokeComposition))
        if is_insertive and curr_word:
            if has_typo:
                self.penalties += 1
            else:
                self.correct_chars += 1

        if not has_typo and is_insertive and (
            len(self.input_val) > len(self.prev_input)
            or (
                len(self.input_val) == 0
                and 0 <= self.word_index - 1 < len(self.words)
                and self.prev_input == self.words[self.word_index - 1]
            )
        ):
            self.combo_counter += 1
            self.longest_combo = max(self.longest_combo, self.combo_counter)
        else:
            self.combo_counter = 0

        if has_typo and not self.prev_has_typo and curr_word:
            self.initial_typo = {
                "charIndex": len(self.wpm_character_times) + _find_first_non_matching(self.input_val, curr_word),
                "wordIndex": self.word_index,
                "time": time_ms,
            }

        if (
            not has_typo
            and self.prev_has_typo
            and self.word_typos
            and self.word_typos[-1].recoveryDelay is None
        ):
            self.word_typos[-1].recoveryDelay = time_delta
            wt = self.word_typos[-1]
            typo_idx = _find_first_non_matching(wt.typo, curr_word)
            anchor = wt.typo[:typo_idx] if typo_idx >= 0 else wt.typo
            self.word_typos[-1].correctionTime = (
                time_ms - (time_delta if isinstance(action, KeystrokeInsert) else 0) - wt.time
            )
            wt.editDistance = _edit_distance(wt.typo, anchor)

        return has_typo

    def _process_word_completions(self, ks: Keystroke) -> None:
        time_ms = ks.time
        curr_word = self._curr_word()
        curr_word_cps = list(curr_word)
        curr_word_cp_len = len(curr_word_cps)

        used_raw_ids = self.global_used_raw_ids
        used_actual_ids = self.global_used_actual_ids

        while (
            curr_word_cp_len > 0
            and len(self.input_val) >= len(curr_word)
            and self.input_val[:curr_word_cp_len] == curr_word
        ):
            raw_times, actual_times = self._compute_word_times(
                curr_word_cps, used_raw_ids, used_actual_ids
            )
            merged_raw, merged_actual = self._merge_combining_marks(raw_times, actual_times)

            raw_word_time = sum(merged_raw)
            self.raw_word_times.append(raw_word_time)
            self.raw_word_times_total += raw_word_time
            self.raw_character_times.extend(merged_raw)

            self._flush_word_graph_points(merged_actual, time_ms)

            cp_end = self.total_chars_before_word + len(self.words[self.word_index]) - 1
            graphemes_completed = (
                self.cp_to_grapheme[cp_end] + 1
                if 0 <= cp_end < len(self.cp_to_grapheme)
                else len(self.wpm_character_times)
            )
            total_chars_count = graphemes_completed + (0 if self.is_multiplayer else -1)

            if self.initial_typo and self.initial_typo["wordIndex"] < len(self.word_wpm_graph_data):
                self.word_wpm_graph_data[self.initial_typo["wordIndex"]].typos = list(self.word_typos)

            wpm_val = calculate_wpm(total_chars_count, time_ms)
            raw_wpm_val = (
                calculate_wpm(total_chars_count, self.raw_word_times_total)
                if self.raw_word_times_total > 0
                else 0.0
            )
            self.word_wpm_graph_data.append(
                WordGraphDataPoint(time=time_ms, wpm=wpm_val, raw=raw_wpm_val, typos=list(self.word_typos))
            )

            self.input_val = self.input_val[curr_word_cp_len:]
            del self.input_val_contributors[:curr_word_cp_len]
            del self.input_val_delays[:curr_word_cp_len]
            self.last_word_completion_time = time_ms
            self.total_chars_before_word += len(curr_word)
            self.word_index += 1
            self.initial_typo = None
            self.word_typos = []
            self.tracking_sequence_pos = -1

            curr_word = self._curr_word()
            curr_word_cps = list(curr_word)
            curr_word_cp_len = len(curr_word_cps)

    def _compute_word_times(
        self,
        curr_word_cps: List[str],
        used_raw_ids: set[int],
        used_actual_ids: set[int],
    ) -> Tuple[List[float], List[float]]:
        curr_word_cp_len = len(curr_word_cps)
        attribution = [-1] * curr_word_cp_len
        raw_times = [0.0] * curr_word_cp_len

        for i in range(curr_word_cp_len):
            abs_pos = self.total_chars_before_word + i

            if (
                i > 0
                and i < len(self.input_val_contributors)
                and i - 1 < len(self.input_val_contributors)
                and self.input_val_contributors[i] >= 0
                and self.input_val_contributors[i] == self.input_val_contributors[i - 1]
            ):
                raw_times[i] = 0
                continue

            if abs_pos in self.post_correction_positions:
                all_at_pos = self.position_keystrokes.get(abs_pos, [])
                expected_char = _normalize_enter(curr_word_cps[i]).lower()
                min_time = float("inf")
                min_ks = -1
                for ks_idx, ks_td in all_at_pos:
                    if (
                        ks_idx in self.fat_finger_times
                        or ks_idx in used_raw_ids
                        or ks_td <= 0
                    ):
                        continue
                    if ks_idx in self.correction_ks_ids:
                        ks_key = _action_key(self.keystrokes[ks_idx].action)
                        typed_char = _normalize_enter(ks_key[0]).lower() if ks_key else ""
                        if typed_char != expected_char:
                            continue
                    if ks_td < min_time:
                        min_time = ks_td
                        min_ks = ks_idx
                if min_ks >= 0:
                    used_raw_ids.add(min_ks)
                    attribution[i] = min_ks
                    raw_times[i] = min_time
                    continue

            keystrokes_at_this = self.position_keystrokes.get(abs_pos, [])
            if keystrokes_at_this:
                expected_char = _normalize_enter(curr_word_cps[i]).lower()
                prev_expected = (
                    _normalize_enter(self.text_cps[abs_pos - 1]).lower()
                    if abs_pos > 0 and abs_pos - 1 < len(self.text_cps)
                    else ""
                )
                next_expected = (
                    _normalize_enter(self.text_cps[abs_pos + 1]).lower()
                    if abs_pos + 1 < len(self.text_cps)
                    else ""
                )
                min_time = float("inf")
                min_ks = -1
                for ks_idx, ks_td in keystrokes_at_this:
                    if ks_idx in self.fat_finger_times or ks_idx in used_raw_ids:
                        continue
                    ks_key = _action_key(self.keystrokes[ks_idx].action)
                    typed_char = _normalize_enter(ks_key[0]).lower() if ks_key else ""
                    is_valid = (
                        typed_char == expected_char
                        or typed_char == prev_expected
                        or typed_char == next_expected
                    )
                    if is_valid and ks_td < min_time:
                        min_time = ks_td
                        min_ks = ks_idx
                if min_ks >= 0:
                    used_raw_ids.add(min_ks)
                    attribution[i] = min_ks
                    raw_times[i] = min_time
                    continue

            expected = curr_word_cps[i]
            normalized_expected = _normalize_enter(expected).lower()
            pool = self.char_pool.get(normalized_expected, [])
            found = False
            for ks_idx, typed_at_pos in pool:
                if (
                    ks_idx not in used_raw_ids
                    and abs(typed_at_pos - abs_pos) <= ATTRIBUTION_WINDOW
                ):
                    used_raw_ids.add(ks_idx)
                    attribution[i] = ks_idx
                    raw_times[i] = self.fat_finger_times.get(ks_idx, self.keystrokes[ks_idx].timeDelta)
                    found = True
                    break

            if not found:
                contrib_id = self.input_val_contributors[i] if i < len(self.input_val_contributors) else -1
                if contrib_id >= 0 and contrib_id not in used_raw_ids:
                    used_raw_ids.add(contrib_id)
                    attribution[i] = contrib_id
                    raw_times[i] = self.keystrokes[contrib_id].timeDelta

        # Inversion adjustment (backwards) — transposed pairs collapse into the earlier char.
        for i in range(curr_word_cp_len - 1, 0, -1):
            ks_prev = attribution[i - 1]
            ks_curr = attribution[i]
            if ks_prev >= 0 and ks_curr >= 0 and ks_prev > ks_curr:
                gap = self.keystrokes[ks_prev].time - self.keystrokes[ks_curr].time
                if gap <= TRANSPOSITION_THRESHOLD_MS:
                    raw_times[i - 1] += raw_times[i]
                    raw_times[i] = 0

        # Fold contributors/delays past the word boundary into the last char's delays.
        last_char_idx = curr_word_cp_len - 1
        ci = curr_word_cp_len
        while ci < len(self.input_val_contributors):
            cid = self.input_val_contributors[ci]
            if cid >= 0 and 0 <= last_char_idx < len(self.input_val_delays):
                self.input_val_delays[last_char_idx].append(cid)
                self.input_val_contributors[ci] = -1
            ci += 1
        ci = curr_word_cp_len
        while ci < len(self.input_val_delays):
            if 0 <= last_char_idx < len(self.input_val_delays):
                self.input_val_delays[last_char_idx].extend(self.input_val_delays[ci])
            self.input_val_delays[ci] = []
            ci += 1

        actual_times: List[float] = []
        for i in range(curr_word_cp_len):
            contrib_id = self.input_val_contributors[i] if i < len(self.input_val_contributors) else -1
            delay_ids = self.input_val_delays[i] if i < len(self.input_val_delays) else []
            actual_time = 0
            if contrib_id >= 0 and contrib_id not in used_actual_ids:
                used_actual_ids.add(contrib_id)
                actual_time += self.keystrokes[contrib_id].timeDelta
            for delay_id in delay_ids:
                if delay_id not in used_actual_ids:
                    used_actual_ids.add(delay_id)
                    actual_time += self.keystrokes[delay_id].timeDelta
            actual_times.append(actual_time)

        return raw_times, actual_times

    def _merge_combining_marks(
        self, raw_times: List[float], actual_times: List[float]
    ) -> Tuple[List[float], List[float]]:
        word_start_cp = self.total_chars_before_word
        merged_raw: List[float] = []
        merged_actual: List[float] = []
        for ci in range(len(raw_times)):
            cp_idx = word_start_cp + ci
            if (
                ci > 0
                and cp_idx > 0
                and cp_idx < len(self.cp_to_grapheme)
                and self.cp_to_grapheme[cp_idx] == self.cp_to_grapheme[cp_idx - 1]
            ):
                merged_raw[-1] += raw_times[ci]
                merged_actual[-1] += actual_times[ci]
            else:
                merged_raw.append(raw_times[ci])
                merged_actual.append(actual_times[ci])
        return merged_raw, merged_actual

    def _flush_word_graph_points(self, merged_actual: List[float], time_ms: int) -> None:
        is_first_word = len(self.wpm_character_times) == 0
        skip_first_char = (
            is_first_word
            and self.is_clean_solo_start
            and (len(merged_actual) == 0 or merged_actual[0] == 0)
        )
        chars_before = (
            1 if skip_first_char else (0 if is_first_word else len(self.wpm_character_times))
        )

        self.wpm_character_times.extend(merged_actual)

        word_start_cp = self.total_chars_before_word

        for i in range(chars_before, len(self.wpm_character_times)):
            self.wpm_running_total += self.wpm_character_times[i]
            self.raw_running_total += self.raw_character_times[i]

            keystroke_total_time = self.wpm_running_total
            if self.is_multiplayer and self.reaction_time > 0:
                keystroke_total_time += self.reaction_time
            if self.is_multiplayer and keystroke_total_time == 0:
                keystroke_total_time = 1

            grapheme_rel_idx = i - chars_before
            if grapheme_rel_idx < len(self.cp_to_grapheme):
                target_g = (
                    self.cp_to_grapheme[word_start_cp] + grapheme_rel_idx
                    if word_start_cp < len(self.cp_to_grapheme)
                    else grapheme_rel_idx
                )
                absolute_char_index = grapheme_rel_idx
                for cp_search, g in enumerate(self.cp_to_grapheme):
                    if g == target_g:
                        absolute_char_index = cp_search
                        break
            else:
                absolute_char_index = grapheme_rel_idx
            char_initial_keystroke_id = (
                self.char_initial_keystroke_ids[absolute_char_index]
                if 0 <= absolute_char_index < len(self.char_initial_keystroke_ids)
                else -1
            )

            typos_here = [t for t in self.word_typos if t.charIndex == i]

            raw_total_time = self.raw_running_total
            if self.is_multiplayer and self.reaction_time > 0:
                raw_total_time += self.reaction_time
            if self.is_multiplayer and raw_total_time == 0:
                raw_total_time = 1

            char_count = i if self.is_clean_solo_start else i + 1
            self.keystrokes_wpm_graph_data.append(
                GraphDataPoint(
                    charIndex=i,
                    wordIndex=self.word_index,
                    initialKeystrokeId=char_initial_keystroke_id,
                    raw=calculate_wpm(char_count, raw_total_time),
                    wpm=calculate_wpm(char_count, keystroke_total_time),
                    time=int(keystroke_total_time),
                    typos=typos_here,
                )
            )
            self.char_typos.extend(typos_here)

    def _check_burst_wpm(self) -> None:
        # Ranked replays must not exceed 1250 WPM over any sliding window.
        if not (self.is_ranked and self.keystrokes_wpm_graph_data):
            return
        window_size = max(10, len(self.text_cps) // 30)
        min_size = 5
        if len(self.keystrokes_wpm_graph_data) < min_size:
            return
        for i in range(min_size - 1, len(self.keystrokes_wpm_graph_data)):
            current = self.keystrokes_wpm_graph_data[i]
            ws_idx = max(i - window_size + 1, 0)
            start_pt = self.keystrokes_wpm_graph_data[ws_idx]
            time_elapsed = current.time - start_pt.time
            char_count = current.charIndex - start_pt.charIndex
            burst_wpm = (char_count / 5) / (time_elapsed / 60000.0) if time_elapsed > 0 else 0
            if burst_wpm > 1250:
                raise InvalidKeystrokeData

    def _finalize(self) -> ProcessResult:
        last_timestamp = self.last_word_completion_time

        processed_graphemes = len(self.wpm_character_times) if self.wpm_character_times else self.grapheme_count
        text_length = processed_graphemes - 1 if self.is_clean_solo_start else processed_graphemes

        total_time_for_wpm = self.wpm_running_total if self.wpm_running_total else last_timestamp
        if self.is_multiplayer and self.reaction_time > 0:
            total_time_for_wpm += self.reaction_time
        wpm_final = calculate_wpm(text_length, total_time_for_wpm)
        if wpm_final == 0:
            raise InvalidKeystrokeData

        overall_wpm_limit = 600 if self.is_ranked else 2750
        if wpm_final > overall_wpm_limit:
            raise InvalidKeystrokeData

        raw_wpm_final = calculate_wpm(
            text_length, self.raw_running_total if self.raw_running_total else last_timestamp
        )

        self._check_burst_wpm()

        denominator = self.correct_chars + self.corrective + self.penalties + self.destructive
        accuracy = 100.0 * (self.correct_chars + self.corrective) / denominator if denominator > 0 else 0.0

        keystroke_wpm_list = [p.wpm or 0.0 for p in self.keystrokes_wpm_graph_data]
        keystroke_raw_wpm_list = [p.raw or 0.0 for p in self.keystrokes_wpm_graph_data]

        return ProcessResult(
            keystrokesWpmGraphData=self.keystrokes_wpm_graph_data,
            wordWpmGraphData=self.word_wpm_graph_data,
            rawCharacterTimes=list(self.raw_character_times),
            wpmCharacterTimes=list(self.wpm_character_times),
            typos=self.char_typos,
            keystrokeWpm=keystroke_wpm_list,
            keystrokeRawWpm=keystroke_raw_wpm_list,
            raw_wpm=raw_wpm_final,
            wpm=wpm_final,
            accuracy=accuracy,
            duration=int(last_timestamp),
        )


def process_keystroke_data(
    keystroke_data: KeystrokeData,
    is_multiplayer: bool = False,
    reaction_time: float = 0,
    is_ranked: bool = False,
) -> ProcessResult:
    """Process a decoded replay into per-character timing, WPM graphs, and accuracy."""
    return _Processor(keystroke_data, is_multiplayer, reaction_time, is_ranked).run()


def get_keystroke_data(
    keystroke_data,
    is_multiplayer: bool = False,
    start_time: float = 0,
) -> ProcessResult:
    """Decode a raw keystroke payload (compact list or legacy dict) and process it."""
    decoded = decode_keystroke_data(keystroke_data)
    return process_keystroke_data(decoded, is_multiplayer, start_time)


def get_keystroke_wpm(delays: list[int], adjusted: bool = True):
    """Returns a list of WPM over keystrokes given a list of ms delays.

    adjusted = True always eliminates the first delay.
    """
    keystroke_wpm = []
    duration = 0

    if delays[0] == 0 or adjusted:
        delays = delays[1:]
        keystroke_wpm = [float("inf")]

    for i, delay in enumerate(delays):
        duration += delay
        wpm = 12000 * (i + 1) / duration if duration else float("inf")
        keystroke_wpm.append(wpm)

    return keystroke_wpm
