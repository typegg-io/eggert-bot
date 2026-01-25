"""Keystroke processing for raw WPM calculation."""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Union

ATTRIBUTION_WINDOW = 7
FAT_FINGER_THRESHOLD_MS = 7
TRANSPOSITION_THRESHOLD_MS = 7


@dataclass
class KeystrokeInsert:
    i: int
    key: str


@dataclass
class KeystrokeDelete:
    dStart: int
    dEnd: int


@dataclass
class KeystrokeReplace:
    rStart: int
    rEnd: int
    redundant: Optional[bool] = None
    key: str = ""


@dataclass
class KeystrokeComposition:
    i: int
    key: str
    steps: List[str] = field(default_factory=list)
    stepTimes: List[int] = field(default_factory=list)


KeystrokeAction = Union[KeystrokeInsert, KeystrokeDelete, KeystrokeReplace, KeystrokeComposition]


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


@dataclass
class KeystrokeTiming:
    ks_id: int
    time_delta: int


@dataclass
class CharPoolEntry:
    ks_id: int
    typed_at_pos: int


@dataclass
class PositionKeystroke:
    ks_id: int
    time_delta: int


@dataclass
class GraphDataPoint:
    charIndex: int
    wordIndex: int
    initialKeystrokeId: int
    wpm: Optional[float] = None
    raw: Optional[float] = None
    time: float = 0.0


@dataclass
class Typo:
    word_index: int
    typo_index: int
    word: str


@dataclass
class ProcessResult:
    keystrokesWpmGraphData: List[GraphDataPoint]
    rawCharacterTimes: List[float]
    wpmCharacterTimes: List[float]
    typos: List[Typo]
    keystrokeWpm: List[float]
    keystrokeRawWpm: List[float]
    raw_wpm: float = 0.0
    wpm: float = 0.0
    accuracy: float = 0.0


def normalize_enter(char: str) -> str:
    if char in ('⏎', '\r\n', '\r'):
        return '\n'
    return char


def split_words(text: str) -> List[str]:
    """Split text into words, matching TypeGG implementation."""
    # 1. Add space after ⏎ if not already present
    result = ""
    for i, c in enumerate(text):
        result += c
        if c == '⏎' and (i + 1 >= len(text) or text[i + 1] != ' '):
            result += ' '
    text = result

    # 2. Replace \r\n with ⏎ (space added)
    text = text.replace('\r\n', '⏎ ')

    # 3. Replace \n with ⏎ (space added)
    text = text.replace('\n', '⏎ ')

    # 4. Split on space
    words = text.split(' ')

    # 5. Add space to words that don't end with ⏎, except last word
    for i in range(len(words) - 1):
        if len(words[i]) > 0 and not words[i].endswith('⏎'):
            words[i] += ' '

    return words


def normalize_for_comparison(s: str) -> str:
    """Normalize string for word completion comparison."""
    return s.replace('⏎', '\n').replace('\r\n', '\n')


def calculate_wpm(chars: int, time_ms: float) -> float:
    if time_ms <= 0:
        return 0.0
    return (chars / 5) * (60000 / time_ms)


def get_key_from_action(action: KeystrokeAction) -> str:
    if isinstance(action, KeystrokeInsert):
        return action.key
    elif isinstance(action, KeystrokeReplace):
        return action.key
    elif isinstance(action, KeystrokeComposition):
        return action.key
    return ''


def process_keystroke_data(
    keystroke_data: KeystrokeData,
    is_multiplayer: bool = False,
    reaction_time: float = 0
) -> ProcessResult:
    keystrokes = keystroke_data.keystrokes
    text = keystroke_data.text.replace('\r\n', '\n')
    words = split_words(text)

    raw_character_times: List[float] = []
    wpm_character_times: List[float] = []
    keystrokes_wpm_graph_data: List[GraphDataPoint] = []

    input_val = ""
    word_index = 0
    buffer_offset = 0

    wpm_running_total = 0.0
    raw_running_total = 0.0
    total_chars_before_word = 0  # cache for chars before current word
    first_char_ime_adjustment = 0.0

    char_pool: Dict[str, List[CharPoolEntry]] = {}
    position_keystrokes: Dict[int, List[PositionKeystroke]] = {}
    post_correction_positions: Set[int] = set()
    fat_finger_times: Dict[int, int] = {}

    correct_chars = 0
    penalties = 0
    corrective = 0
    destructive = 0

    typos: List[Typo] = []
    typo_flag = False

    prev_was_insert = False
    prev_insert_ks_id = -1
    prev_insert_key = ""
    prev_insert_pos = -1

    # Tracking sequence: tracks valid positions when typing at wrong position
    tracking_sequence_pos = -1

    def find_char_in_text(char: str, start_from: int) -> int:
        """Find where a char appears in the text (for starting a tracking sequence)."""
        normalized_char = normalize_enter(char)
        for i in range(start_from, len(text)):
            if normalize_enter(text[i]) == normalized_char:
                return i
        return -1

    global_used_raw_ids: Set[int] = set()
    global_used_actual_ids: Set[int] = set()

    input_val_contributors: List[int] = []
    input_val_delays: List[List[int]] = []
    pending_delays: List[int] = []

    def get_absolute_position(relative_position: int) -> int:
        return total_chars_before_word + relative_position

    def add_to_char_pool(char: str, ks_id: int, typed_at_pos: int):
        normalized = normalize_enter(char).lower()
        if normalized not in char_pool:
            char_pool[normalized] = []
        char_pool[normalized].append(CharPoolEntry(ks_id=ks_id, typed_at_pos=typed_at_pos))

    def add_to_position_keystrokes(pos: int, ks_id: int, time_delta: int):
        if pos not in position_keystrokes:
            position_keystrokes[pos] = []
        position_keystrokes[pos].append(PositionKeystroke(ks_id=ks_id, time_delta=time_delta))

    for keystroke_id, keystroke in enumerate(keystrokes):
        action = keystroke.action
        time = keystroke.time
        time_delta = keystroke.timeDelta

        current_word = words[word_index] if word_index < len(words) else ""
        # Use cached value instead of O(n) sum

        if isinstance(action, KeystrokeInsert):
            i = max(0, min(action.i, len(input_val)))
            typed_char = action.key
            absolute_pos = get_absolute_position(i)

            # Fat-finger: wrong char immediately followed by correct char for PREV position
            # This detects inversions where user typed two chars quickly but in wrong order
            if (prev_was_insert and
                time_delta <= FAT_FINGER_THRESHOLD_MS and
                prev_insert_pos >= 0 and prev_insert_pos < len(text)):

                expected_prev = normalize_enter(text[prev_insert_pos]).lower()
                typed_prev = normalize_enter(prev_insert_key).lower()
                typed_curr = normalize_enter(typed_char).lower()

                # Fat-finger: prev was wrong, current is correct for PREV position
                if typed_prev != expected_prev and typed_curr == expected_prev:
                    # Add to charPool at prev position
                    add_to_char_pool(text[prev_insert_pos], keystroke_id, prev_insert_pos)
                    # Store combined time
                    prev_time_delta = keystrokes[prev_insert_ks_id].timeDelta
                    if prev_insert_ks_id in fat_finger_times:
                        prev_time_delta = fat_finger_times[prev_insert_ks_id]
                    fat_finger_times[keystroke_id] = prev_time_delta + time_delta

            input_val = input_val[:i] + typed_char + input_val[i:]

            adj_i = i + buffer_offset
            if adj_i >= len(input_val_contributors):
                input_val_contributors.append(keystroke_id)
                input_val_delays.append(list(pending_delays) if pending_delays else [])
            else:
                # When inserting in the middle, merge existing delays at this position
                # with pending_delays. This handles the case where DELETE added delays
                # to a position, and now INSERT is typing a new character there.
                existing_delays = input_val_delays[adj_i] if adj_i < len(input_val_delays) else []
                merged_delays = list(pending_delays) + existing_delays
                input_val_contributors.insert(adj_i, keystroke_id)
                input_val_delays.insert(adj_i, merged_delays)
            pending_delays.clear()

            # Always add to position_keystrokes at absolute_pos
            add_to_position_keystrokes(absolute_pos, keystroke_id, time_delta)

            # Tracking sequence logic for char_pool (matches Go implementation)
            if typed_char:
                normalized_typed = normalize_enter(typed_char).lower()
                expected_char = ""
                if 0 <= absolute_pos < len(text):
                    expected_char = normalize_enter(text[absolute_pos]).lower()

                exact_match = (0 <= absolute_pos < len(text) and normalized_typed == expected_char)
                case_insensitive_match = (not exact_match and 0 <= absolute_pos < len(text) and
                                          normalized_typed == expected_char)

                if exact_match or case_insensitive_match:
                    # Rule 1: Correct position - add at absolute_pos
                    add_to_char_pool(typed_char, keystroke_id, absolute_pos)
                    tracking_sequence_pos = absolute_pos + 1
                elif (tracking_sequence_pos >= 0 and tracking_sequence_pos < len(text) and
                      normalized_typed == normalize_enter(text[tracking_sequence_pos]).lower()):
                    # Rule 2: Continues tracking sequence - add at tracking_sequence_pos
                    add_to_char_pool(typed_char, keystroke_id, tracking_sequence_pos)
                    tracking_sequence_pos += 1
                else:
                    # Rule 3: Try to start new tracking sequence (don't add to char_pool)
                    match_pos = find_char_in_text(typed_char, 0)
                    if match_pos >= 0:
                        tracking_sequence_pos = match_pos + 1
                    else:
                        tracking_sequence_pos = -1

            prev_was_insert = True
            prev_insert_ks_id = keystroke_id
            prev_insert_key = typed_char
            prev_insert_pos = absolute_pos

        elif isinstance(action, KeystrokeReplace):
            r_start = max(0, min(action.rStart, len(input_val)))
            r_end = max(0, min(action.rEnd, len(input_val)))
            typed_char = action.key
            absolute_pos = get_absolute_position(r_start)
            adj_start = r_start + buffer_offset

            if action.redundant:
                # Redundant replace: add keystroke to delays BEFORE buffer update
                if adj_start >= 0 and adj_start < len(input_val_delays):
                    input_val_delays[adj_start].append(keystroke_id)
                else:
                    # Position doesn't exist - add to pending delays
                    pending_delays.append(keystroke_id)
                destructive += 1
            else:
                # Non-redundant: count corrective/destructive for deletion part
                for del_pos in range(r_start, r_end):
                    if del_pos < len(input_val):
                        deleted_char = input_val[del_pos]
                        if del_pos < len(current_word):
                            expected_char = current_word[del_pos]
                            if deleted_char != expected_char:
                                corrective += 1
                            else:
                                destructive += 1
                        else:
                            corrective += 1
                # Count for insertion part
                if r_start < len(current_word):
                    if typed_char == current_word[r_start]:
                        corrective += 1
                    else:
                        destructive += 1
                else:
                    destructive += 1

                # Non-redundant: collect preserved IDs and modify arrays
                adj_end = r_end + buffer_offset

                preserved_ids: List[int] = []
                for j in range(adj_start, min(adj_end, len(input_val_contributors))):
                    if input_val_contributors[j] >= 0:
                        preserved_ids.append(input_val_contributors[j])
                    preserved_ids.extend(input_val_delays[j])

                del input_val_contributors[adj_start:adj_end]
                del input_val_delays[adj_start:adj_end]

                while len(input_val_contributors) <= adj_start:
                    input_val_contributors.append(-1)
                    input_val_delays.append([])
                input_val_contributors.insert(adj_start, keystroke_id)
                input_val_delays.insert(adj_start, preserved_ids + list(pending_delays))
                pending_delays.clear()

            if r_start <= r_end:
                input_val = input_val[:r_start] + typed_char + input_val[r_end:]

            # Add to charPool/positionKeystrokes for ALL REPLACEs when buffer update succeeds
            if r_start <= r_end and typed_char:
                add_to_position_keystrokes(absolute_pos, keystroke_id, time_delta)

                # Mark as post-correction for ALL REPLACE (not just non-redundant)
                if 0 <= absolute_pos < len(text):
                    post_correction_positions.add(absolute_pos)

                normalized_typed = normalize_enter(typed_char).lower()

                # Fat-finger detection for REPLACE (same as INSERT)
                if (prev_was_insert and
                    time_delta <= FAT_FINGER_THRESHOLD_MS and
                    prev_insert_pos >= 0 and prev_insert_pos < len(text)):

                    expected_prev = normalize_enter(text[prev_insert_pos]).lower()
                    typed_prev = normalize_enter(prev_insert_key).lower()
                    typed_curr = normalized_typed

                    # Fat-finger: prev was wrong, current is correct for PREV position
                    if typed_prev != expected_prev and typed_curr == expected_prev:
                        add_to_char_pool(text[prev_insert_pos], keystroke_id, prev_insert_pos)
                        prev_time_delta = keystrokes[prev_insert_ks_id].timeDelta
                        if prev_insert_ks_id in fat_finger_times:
                            prev_time_delta = fat_finger_times[prev_insert_ks_id]
                        fat_finger_times[keystroke_id] = prev_time_delta + time_delta

                # Tracking sequence logic for char_pool
                expected_char = ""
                if 0 <= absolute_pos < len(text):
                    expected_char = normalize_enter(text[absolute_pos]).lower()

                if 0 <= absolute_pos < len(text) and normalized_typed == expected_char:
                    # Correct position - add at absolute_pos
                    add_to_char_pool(typed_char, keystroke_id, absolute_pos)
                    tracking_sequence_pos = absolute_pos + 1
                elif (tracking_sequence_pos >= 0 and tracking_sequence_pos < len(text) and
                      normalized_typed == normalize_enter(text[tracking_sequence_pos]).lower()):
                    # Continues tracking sequence - add at tracking_sequence_pos
                    add_to_char_pool(typed_char, keystroke_id, tracking_sequence_pos)
                    tracking_sequence_pos += 1
                else:
                    # Try to start new tracking sequence (don't add to char_pool)
                    match_pos = find_char_in_text(typed_char, 0)
                    if match_pos >= 0:
                        tracking_sequence_pos = match_pos + 1
                    else:
                        tracking_sequence_pos = -1

                # Update prev_insert info for fat-finger detection (like INSERT)
                prev_was_insert = True
                prev_insert_ks_id = keystroke_id
                prev_insert_key = typed_char
                prev_insert_pos = absolute_pos
            else:
                prev_was_insert = False

        elif isinstance(action, KeystrokeDelete):
            d_start = max(0, min(action.dStart, len(input_val)))
            d_end = max(0, min(action.dEnd, len(input_val)))

            if d_start > d_end:
                d_start, d_end = d_end, d_start

            # Count corrective/destructive for each deleted character
            for del_pos in range(d_start, d_end):
                if del_pos < len(input_val):
                    deleted_char = input_val[del_pos]
                    if del_pos < len(current_word):
                        expected_char = current_word[del_pos]
                        if deleted_char == expected_char:
                            destructive += 1
                        else:
                            corrective += 1
                    else:
                        corrective += 1

            input_val = input_val[:d_start] + input_val[d_end:]

            adj_start = d_start + buffer_offset
            adj_end = d_end + buffer_offset

            preserved_ids: List[int] = [keystroke_id]
            for j in range(adj_start, min(adj_end, len(input_val_contributors))):
                if input_val_contributors[j] >= 0:
                    preserved_ids.append(input_val_contributors[j])

            del input_val_contributors[adj_start:adj_end]
            del input_val_delays[adj_start:adj_end]

            if adj_start < len(input_val_delays):
                input_val_delays[adj_start] = input_val_delays[adj_start] + preserved_ids
            else:
                pending_delays.extend(preserved_ids)

            tail_pos = total_chars_before_word + d_start
            if 0 <= tail_pos < len(text):
                post_correction_positions.add(tail_pos)

            # Reset tracking sequence on delete (buffer changed significantly)
            tracking_sequence_pos = -1
            prev_was_insert = False

        elif isinstance(action, KeystrokeComposition):
            typed_chars = action.key
            insert_pos = max(0, min(action.i, len(input_val)))
            absolute_pos = get_absolute_position(insert_pos)

            input_val = input_val[:insert_pos] + typed_chars + input_val[insert_pos:]

            for idx, char in enumerate(typed_chars):
                pos = absolute_pos + idx
                add_to_char_pool(char, keystroke_id, pos)
                add_to_position_keystrokes(pos, keystroke_id, time_delta if idx == 0 else 0)

                adj_i = insert_pos + idx + buffer_offset
                while len(input_val_contributors) <= adj_i:
                    input_val_contributors.append(-1)
                    input_val_delays.append([])
                input_val_contributors.insert(adj_i, keystroke_id if idx == 0 else -1)
                input_val_delays.insert(adj_i, list(pending_delays) if idx == 0 else [])
                if idx == 0:
                    pending_delays.clear()

            prev_was_insert = False

        # accuracy calc
        has_typo = False
        if current_word:
            compare_len = min(len(input_val), len(current_word))
            has_typo = input_val[:compare_len] != current_word[:compare_len]

        has_key = isinstance(action, (KeystrokeInsert, KeystrokeReplace, KeystrokeComposition))
        if has_key:
            if has_typo:
                penalties += 1
            else:
                correct_chars += 1

        # Typo tracking: record when transitioning from correct to incorrect state
        # Only for insert-type actions (not deletes/backspaces)
        is_insert_action = isinstance(action, (KeystrokeInsert, KeystrokeComposition)) or (
            isinstance(action, KeystrokeReplace) and not action.redundant
        )
        if has_typo and not typo_flag and is_insert_action:
            typo_flag = True
            typo_index = total_chars_before_word + len(input_val) - 1
            typos.append(Typo(
                word_index=word_index,
                typo_index=typo_index,
                word=current_word.rstrip(),
            ))
        elif not has_typo and typo_flag:
            typo_flag = False

        # Word completion
        while (current_word and
               len(input_val) >= len(current_word) and
               input_val[:len(current_word)] == current_word and
               word_index < len(words)):

            raw_times_for_word: List[float] = []
            actual_times_for_word: List[float] = []

            attribution: List[int] = [-1] * len(current_word)
            raw_times: List[float] = [0.0] * len(current_word)

            for i in range(len(current_word)):
                absolute_pos = total_chars_before_word + i
                expected_char = normalize_enter(current_word[i]).lower()

                # Post-correction: use min time from keystrokes that typed the expected char
                if absolute_pos in post_correction_positions:
                    all_at_pos = position_keystrokes.get(absolute_pos, [])
                    min_time = float('inf')
                    min_ks_id = -1

                    for pk in all_at_pos:
                        if pk.ks_id in fat_finger_times or pk.ks_id in global_used_raw_ids:
                            continue

                        typed_char = get_key_from_action(keystrokes[pk.ks_id].action)
                        typed_normalized = normalize_enter(typed_char).lower()

                        if typed_normalized == expected_char and pk.time_delta < min_time:
                            min_time = pk.time_delta
                            min_ks_id = pk.ks_id

                    if min_ks_id >= 0:
                        global_used_raw_ids.add(min_ks_id)
                        attribution[i] = min_ks_id
                        raw_times[i] = min_time
                        continue

                # Check for inversions (transpositions)
                keystrokes_at_pos = position_keystrokes.get(absolute_pos, [])
                if keystrokes_at_pos:
                    prev_expected = ""
                    next_expected = ""
                    if absolute_pos > 0 and absolute_pos - 1 < len(text):
                        prev_expected = normalize_enter(text[absolute_pos - 1]).lower()
                    if absolute_pos + 1 < len(text):
                        next_expected = normalize_enter(text[absolute_pos + 1]).lower()

                    min_time = float('inf')
                    min_ks_id = -1

                    for pk in keystrokes_at_pos:
                        if pk.ks_id in fat_finger_times or pk.ks_id in global_used_raw_ids:
                            continue

                        typed_char = get_key_from_action(keystrokes[pk.ks_id].action)
                        typed_normalized = normalize_enter(typed_char).lower()

                        is_valid = (typed_normalized == expected_char or
                                    typed_normalized == prev_expected or
                                    typed_normalized == next_expected)

                        if is_valid and pk.time_delta < min_time:
                            min_time = pk.time_delta
                            min_ks_id = pk.ks_id

                    if min_ks_id >= 0:
                        global_used_raw_ids.add(min_ks_id)
                        attribution[i] = min_ks_id
                        raw_times[i] = min_time
                        continue

                # Char pool (left-to-right attribution)
                pool = char_pool.get(expected_char, [])
                found_in_pool = False

                for entry in pool:
                    if entry.ks_id not in global_used_raw_ids:
                        if abs(entry.typed_at_pos - absolute_pos) <= ATTRIBUTION_WINDOW:
                            global_used_raw_ids.add(entry.ks_id)
                            attribution[i] = entry.ks_id

                            if entry.ks_id in fat_finger_times:
                                raw_times[i] = fat_finger_times[entry.ks_id]
                            else:
                                raw_times[i] = keystrokes[entry.ks_id].timeDelta

                            found_in_pool = True
                            break

                if not found_in_pool:
                    adj_i = i + buffer_offset
                    contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                    if contributor_id >= 0 and contributor_id not in global_used_raw_ids:
                        global_used_raw_ids.add(contributor_id)
                        attribution[i] = contributor_id
                        raw_times[i] = keystrokes[contributor_id].timeDelta

            # Transposition time combining
            for i in range(len(current_word) - 1, 0, -1):
                ks_prev = attribution[i - 1]
                ks_curr = attribution[i]

                if ks_prev >= 0 and ks_curr >= 0 and ks_prev > ks_curr:
                    gap = keystrokes[ks_prev].time - keystrokes[ks_curr].time
                    if gap <= TRANSPOSITION_THRESHOLD_MS:
                        raw_times[i - 1] += raw_times[i]
                        raw_times[i] = 0

            raw_times_for_word = raw_times

            # Actual WPM: contributor + delays
            for i in range(len(current_word)):
                adj_i = i + buffer_offset
                contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                delay_ids = input_val_delays[adj_i] if adj_i < len(input_val_delays) else []

                actual_time = 0.0
                if contributor_id >= 0 and contributor_id not in global_used_actual_ids:
                    global_used_actual_ids.add(contributor_id)
                    actual_time += keystrokes[contributor_id].timeDelta

                    # for first character in solo mode with IME, subtract first step time for adjusted wpm
                    is_first_char_overall = len(wpm_character_times) == 0 and i == 0
                    if is_first_char_overall and not is_multiplayer and actual_time > 0:
                        action = keystrokes[contributor_id].action
                        if isinstance(action, KeystrokeComposition) and len(action.stepTimes) > 1:
                            ime_step_time = action.stepTimes[1]
                            actual_time -= ime_step_time
                            first_char_ime_adjustment = ime_step_time

                for delay_id in delay_ids:
                    if delay_id not in global_used_actual_ids:
                        global_used_actual_ids.add(delay_id)
                        actual_time += keystrokes[delay_id].timeDelta

                actual_times_for_word.append(actual_time)

            raw_character_times.extend(raw_times_for_word)

            is_first_word = len(wpm_character_times) == 0
            first_char_time_is_zero = len(actual_times_for_word) > 0 and actual_times_for_word[0] == 0.0

            if is_first_word:
                if not is_multiplayer and first_char_time_is_zero:
                    chars_before = 1  # Solo with non-IME: skip first char
                else:
                    chars_before = 0  # Multiplayer OR IME: include first char
            else:
                chars_before = len(wpm_character_times)

            wpm_character_times.extend(actual_times_for_word)

            for i in range(chars_before, len(wpm_character_times)):
                wpm_running_total += wpm_character_times[i]
                raw_running_total += raw_character_times[i]

                wpm_total_time = wpm_running_total
                raw_total_time = raw_running_total

                if is_multiplayer and reaction_time > 0:
                    wpm_total_time += reaction_time
                    raw_total_time += reaction_time

                absolute_char_index = total_chars_before_word + (i - chars_before)
                initial_ks_id = attribution[i - chars_before] if (i - chars_before) < len(attribution) else -1

                keystrokes_wpm_graph_data.append(
                    GraphDataPoint(
                        charIndex=i,
                        wordIndex=word_index,
                        initialKeystrokeId=initial_ks_id,
                        raw=calculate_wpm(i + (1 if is_multiplayer else 0), raw_total_time),
                        wpm=calculate_wpm(i + (1 if is_multiplayer else 0), wpm_total_time),
                        time=wpm_total_time
                    )
                )

            input_val = input_val[len(current_word):]
            buffer_offset = 0
            input_val_contributors = input_val_contributors[len(current_word):]
            input_val_delays = [list(d) for d in input_val_delays[len(current_word):]]

            total_chars_before_word += len(current_word)
            word_index += 1
            # Reset tracking sequence for new word context
            tracking_sequence_pos = -1
            current_word = words[word_index] if word_index < len(words) else ""

    # === FIX FOR CASCADING SPACE KEYSTROKE BUG ===
    # After all words are processed, there may be remaining unattributed keystrokes
    # in input_val_contributors (e.g., a trailing space that cascaded from the previous word).
    # We must attribute these to the running total so that sum(wpm_character_times) == last_timestamp.
    if keystrokes_wpm_graph_data:
        additional_time = 0.0

        # attribute any remaining contributors
        for contributor_id in input_val_contributors:
            if contributor_id >= 0 and contributor_id not in global_used_actual_ids:
                global_used_actual_ids.add(contributor_id)
                additional_time += keystrokes[contributor_id].timeDelta

        # attribute any remaining delays
        for delay_ids in input_val_delays:
            for delay_id in delay_ids:
                if delay_id not in global_used_actual_ids:
                    global_used_actual_ids.add(delay_id)
                    additional_time += keystrokes[delay_id].timeDelta

        # attribute any pending delays (from DELETEs that cleared the buffer without subsequent INSERTs)
        for delay_id in pending_delays:
            if delay_id not in global_used_actual_ids:
                global_used_actual_ids.add(delay_id)
                additional_time += keystrokes[delay_id].timeDelta

        # add any remaining time to the running total and update last graph point.
        # my attempt at a "best effort" fix in case the user messes with input so much we can no longer attribute correctly
        if additional_time > 0 and wpm_character_times:
            wpm_character_times[-1] += additional_time
            wpm_running_total += additional_time  # Update running total too

            last_point = keystrokes_wpm_graph_data[-1]
            text_len = len(text) - 1
            total_time = wpm_running_total
            last_point.wpm = calculate_wpm(text_len, total_time)
            last_point.time = total_time

    text_length = len(text) - 1
    total_raw_time = raw_running_total

    last_timestamp = keystrokes[-1].time if keystrokes else 0

    total_time_for_wpm = last_timestamp
    if not is_multiplayer:
        total_time_for_wpm -= first_char_ime_adjustment

    raw_wpm = calculate_wpm(text_length, total_raw_time) if total_raw_time > 0 else 0.0
    wpm = calculate_wpm(text_length, total_time_for_wpm) if total_time_for_wpm > 0 else 0.0

    denominator = correct_chars + corrective + penalties + destructive
    accuracy = 100.0 * (correct_chars + corrective) / denominator if denominator > 0 else 0.0

    keystroke_wpm = [point.wpm for point in keystrokes_wpm_graph_data]
    keystroke_raw_wpm = [point.raw for point in keystrokes_wpm_graph_data]

    return ProcessResult(
        keystrokesWpmGraphData=keystrokes_wpm_graph_data,
        rawCharacterTimes=raw_character_times,
        wpmCharacterTimes=wpm_character_times,
        typos=typos,
        keystrokeWpm=keystroke_wpm,
        keystrokeRawWpm=keystroke_raw_wpm,
        raw_wpm=raw_wpm,
        wpm=wpm,
        accuracy=accuracy
    )


def get_keystroke_data(keystroke_data: list) -> ProcessResult:
    """Decode and process raw keystroke data into WPM metrics, timing data, and typos."""
    from utils.keystroke_codec import decode_keystroke_data

    decoded_data = decode_keystroke_data(keystroke_data)
    processed_data = process_keystroke_data(decoded_data)

    return processed_data


def get_keystroke_wpm(delays: list[int], adjusted: bool = True):
    """
    Returns a list of WPM over keystrokes given a list of ms delays.
    adjusted = True will always eliminate the first delay.
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
