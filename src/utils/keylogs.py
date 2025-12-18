import re
from typing import Optional

# Transposition threshold: when keystrokes are typed in wrong order (inverted)
# and close together in time, combine their times for raw WPM calculation
# (also used for fatfinger detection)
TRANSPOSITION_THRESHOLD_MS = 7

# Attribution window: keystrokes can only be attributed to positions within this many
# characters of where they were originally typed (prevents inflated raw WPM from spam)
ATTRIBUTION_WINDOW = 7


def get_keystroke_data(keystroke_data: dict):
    """
    Parses keystroke data to calculate per-character WPM and raw WPM using
    post-hoc attribution algorithm (matching frontend/backend implementations).

    WPM: Uses contributor + delays (accounts for corrections)
    Raw WPM: Uses left-to-right attribution + tracking sequence + transposition adjustment
    """
    newline = {"⏎": "\n"}

    codec_version, text, sticky_start, event_data = keystroke_data
    text = text.replace("\r\n", "\n")
    words = re.findall(r".*?(?: |\n|$)", text)[:-1]

    # Typo tracking
    typos = []
    typo_flag = False

    # Post-hoc timing attribution
    input_val_contributors: list[int] = []  # keystroke ID that typed each position
    input_val_delays: list[list[int]] = []  # delay IDs for each position
    buffer_offset = 0  # virtual offset for O(1) word completion
    pending_delays: list[int] = []  # delays waiting for next insert

    # Character pool: tracks all keystrokes that typed each character (for left-to-right attribution)
    # char -> array of (keystroke ID, position where typed) tuples in chronological order
    char_pool: dict[str, list[tuple[int, int]]] = {}

    # Fat-finger detection: when you type any wrong char then quickly type the correct char,
    # combine times and add to pool. Maps keystrokeId -> combined time
    fat_finger_times: dict[int, int] = {}

    # Track previous keystroke info for fat-finger detection
    prev_insert_key: Optional[str] = None
    prev_insert_index: Optional[int] = None
    prev_insert_keystroke_id: int = -1

    # Tracking sequence: when a char is typed at wrong position but matches somewhere in text,
    # we track subsequent chars to see if they continue a valid sequence.
    # -1 means no active tracking; >= 0 means expecting text[tracking_sequence_pos] next
    tracking_sequence_pos = -1

    # Attribution start tracking: we only start using char_pool attribution once we see a position
    # typed correctly for the SECOND time (pigeonhole principle - if every position is typed
    # exactly once and quote completes, user had 100% accuracy, so raw = wpm)
    # Before that point, raw time = contributor time (1:1 mapping)
    positions_typed_correctly: set[int] = set()
    attribution_started = False
    attribution_started_at_position = -1  # absolute text position where attribution starts

    # Character timing results
    wpm_character_times: list[float] = []
    raw_character_times: list[float] = []

    # State
    input_box: list[str] = []
    typed_words: list[str] = []
    word_index = 0
    total_chars_before_word = 0

    def normalize_enter(char: str) -> str:
        """Normalize enter characters: treat ⏎, \\n, and \\r as equivalent."""
        if char == "\n" or char == "\r":
            return "⏎"
        return char

    def track_correct_position(absolute_pos: int):
        """Track that a position was typed correctly. Sets attribution_started if seen twice."""
        nonlocal attribution_started, attribution_started_at_position
        if absolute_pos in positions_typed_correctly:
            # This position was already typed correctly before - start attribution!
            if not attribution_started:
                attribution_started = True
                attribution_started_at_position = absolute_pos
        positions_typed_correctly.add(absolute_pos)

    def add_to_char_pool(char: str, keystroke_id: int, typed_at_pos: int):
        """Add a keystroke to the character pool (normalizes enter chars and lowercases for case-insensitive matching)."""
        normalized = normalize_enter(char).lower()
        if normalized not in char_pool:
            char_pool[normalized] = []
        char_pool[normalized].append((keystroke_id, typed_at_pos))

    def find_char_in_text(char: str, start_from: int = 0) -> int:
        """Find where a char appears in text (normalizes enter chars for comparison)."""
        normalized_char = normalize_enter(char)
        for i in range(start_from, len(text)):
            if normalize_enter(text[i]) == normalized_char:
                return i
        return -1

    # Global tracking sets to prevent double-counting across entire replay
    # Each keystroke should only contribute its timing to ONE character position
    global_used_raw_ids: set[int] = set()
    global_used_actual_ids: set[int] = set()

    # Post-correction position tracking:
    # Track ALL keystrokes at each position (regardless of character correctness)
    # Used for post-correction positions to find minimum non-fatfinger time
    position_keystrokes: dict[int, list[tuple[int, int, str]]] = {}  # pos -> [(ks_id, time_delta, typed_char), ...]

    # Track positions that are "post-correction first positions"
    # These occur at: (1) tail position after DELETE, (2) r_start position of REPLACE
    # For these positions, use minimum non-fatfinger time instead of earliest char_pool match
    post_correction_positions: set[int] = set()

    def add_to_position_keystrokes(absolute_pos: int, keystroke_id: int, time_delta: int, typed_char: str):
        """Track ALL keystrokes at each position (for post-correction minimum time lookup)."""
        if absolute_pos not in position_keystrokes:
            position_keystrokes[absolute_pos] = []
        position_keystrokes[absolute_pos].append((keystroke_id, time_delta, typed_char))

    # CODEC_VERSION 1
    events = re.split(r"\|(?=\d)", event_data)
    event_re = re.compile(r"^(\d+)(.)(.*)$")

    time_deltas: list[int] = []
    prev_was_insert = False

    for keystroke_id, event in enumerate(events):
        match = event_re.match(event)
        if not match:
            continue
        time_delta_str, action, params = match.groups()
        time_delta = int(time_delta_str)
        time_deltas.append(time_delta)

        current_word = words[word_index] if word_index < len(words) else ""

        # Insert (append)
        if action == "+":
            key = newline.get(params, params)
            index = len(input_box)
            input_box.append(key)

            # Track contributor
            adjusted_i = index + buffer_offset
            if adjusted_i >= len(input_val_contributors):
                input_val_contributors.append(keystroke_id)
                input_val_delays.append(pending_delays[:] if pending_delays else [])
            else:
                input_val_contributors.insert(adjusted_i, keystroke_id)
                input_val_delays.insert(adjusted_i, pending_delays[:] if pending_delays else [])
            pending_delays = []

            # Add to character pool with tracking sequence logic
            absolute_pos = total_chars_before_word + index

            # Track ALL keystrokes at each position (for post-correction minimum time lookup)
            add_to_position_keystrokes(absolute_pos, keystroke_id, time_delta, key)

            normalized_key = normalize_enter(key)

            # Fat-finger detection: if previous keystroke was wrong and this one is correct for prev position
            if (prev_was_insert and prev_insert_key is not None and
                prev_insert_index is not None and prev_insert_keystroke_id >= 0 and
                time_delta <= TRANSPOSITION_THRESHOLD_MS):
                prev_abs_pos = total_chars_before_word + prev_insert_index
                if (0 <= prev_abs_pos < len(text) and
                    normalize_enter(prev_insert_key) != normalize_enter(text[prev_abs_pos]) and
                    normalized_key == normalize_enter(text[prev_abs_pos])):
                    # Fat-finger detected: prev was wrong, current is correct for prev position
                    track_correct_position(prev_abs_pos)
                    add_to_char_pool(text[prev_abs_pos], keystroke_id, prev_abs_pos)
                    prev_time = fat_finger_times.get(prev_insert_keystroke_id, time_deltas[prev_insert_keystroke_id])
                    fat_finger_times[keystroke_id] = prev_time + time_delta

            expected_char = normalize_enter(text[absolute_pos]) if 0 <= absolute_pos < len(text) else ""
            exact_match = 0 <= absolute_pos < len(text) and normalized_key == expected_char
            case_insensitive_match = not exact_match and 0 <= absolute_pos < len(text) and normalized_key.lower() == expected_char.lower()

            if exact_match or case_insensitive_match:
                # Rule 1: Correct position (exact or case-insensitive) - always add
                if exact_match:
                    track_correct_position(absolute_pos)
                add_to_char_pool(key, keystroke_id, absolute_pos)
                tracking_sequence_pos = absolute_pos + 1
            elif 0 <= tracking_sequence_pos < len(text) and normalized_key.lower() == normalize_enter(text[tracking_sequence_pos]).lower():
                # Rule 2: Continues active tracking sequence - add and advance
                track_correct_position(tracking_sequence_pos)
                add_to_char_pool(key, keystroke_id, tracking_sequence_pos)
                tracking_sequence_pos += 1
            else:
                # Rule 3: Try to start new tracking sequence
                match_pos = find_char_in_text(key, 0)
                if match_pos >= 0:
                    tracking_sequence_pos = match_pos + 1
                else:
                    tracking_sequence_pos = -1

            # Update previous keystroke info for fat-finger detection
            prev_insert_key = key
            prev_insert_index = index
            prev_insert_keystroke_id = keystroke_id
            prev_was_insert = True

        # Insert (at pos)
        elif action == ">":
            key = newline.get(params[-1], params[-1])
            index = int(params[:-2])

            if index >= len(input_box):
                input_box.extend([""] * (index + 1 - len(input_box)))
            input_box[index] = key

            # Track contributor
            adjusted_i = index + buffer_offset
            if adjusted_i >= len(input_val_contributors):
                while len(input_val_contributors) <= adjusted_i:
                    input_val_contributors.append(-1)
                    input_val_delays.append([])
                input_val_contributors[adjusted_i] = keystroke_id
                input_val_delays[adjusted_i] = pending_delays[:] if pending_delays else []
            else:
                input_val_contributors.insert(adjusted_i, keystroke_id)
                input_val_delays.insert(adjusted_i, pending_delays[:] if pending_delays else [])
            pending_delays = []

            # Add to character pool with tracking sequence logic
            absolute_pos = total_chars_before_word + index

            # Track ALL keystrokes at each position (for post-correction minimum time lookup)
            add_to_position_keystrokes(absolute_pos, keystroke_id, time_delta, key)

            normalized_key = normalize_enter(key)

            # Fat-finger detection for insert at pos (same as append)
            if (prev_was_insert and prev_insert_key is not None and
                prev_insert_index is not None and prev_insert_keystroke_id >= 0 and
                time_delta <= TRANSPOSITION_THRESHOLD_MS):
                prev_abs_pos = total_chars_before_word + prev_insert_index
                if (0 <= prev_abs_pos < len(text) and
                    normalize_enter(prev_insert_key) != normalize_enter(text[prev_abs_pos]) and
                    normalized_key == normalize_enter(text[prev_abs_pos])):
                    # Fat-finger detected: prev was wrong, current is correct for prev position
                    track_correct_position(prev_abs_pos)
                    add_to_char_pool(text[prev_abs_pos], keystroke_id, prev_abs_pos)
                    prev_time = fat_finger_times.get(prev_insert_keystroke_id, time_deltas[prev_insert_keystroke_id])
                    fat_finger_times[keystroke_id] = prev_time + time_delta

            expected_char = normalize_enter(text[absolute_pos]) if 0 <= absolute_pos < len(text) else ""
            exact_match = 0 <= absolute_pos < len(text) and normalized_key == expected_char
            case_insensitive_match = not exact_match and 0 <= absolute_pos < len(text) and normalized_key.lower() == expected_char.lower()

            if exact_match or case_insensitive_match:
                # Rule 1: Correct position (exact or case-insensitive) - always add
                if exact_match:
                    track_correct_position(absolute_pos)
                add_to_char_pool(key, keystroke_id, absolute_pos)
                tracking_sequence_pos = absolute_pos + 1
            elif 0 <= tracking_sequence_pos < len(text) and normalized_key.lower() == normalize_enter(text[tracking_sequence_pos]).lower():
                # Rule 2: Continues active tracking sequence - add and advance
                track_correct_position(tracking_sequence_pos)
                add_to_char_pool(key, keystroke_id, tracking_sequence_pos)
                tracking_sequence_pos += 1
            else:
                # Rule 3: Try to start new tracking sequence
                match_pos = find_char_in_text(key, 0)
                if match_pos >= 0:
                    tracking_sequence_pos = match_pos + 1
                else:
                    tracking_sequence_pos = -1

            # Update previous keystroke info for fat-finger detection
            prev_insert_key = key
            prev_insert_index = index
            prev_insert_keystroke_id = keystroke_id
            prev_was_insert = True

        # Delete (backspace)
        elif action == "<":
            if input_box:
                d_start = len(input_box) - 1
                d_end = len(input_box)

                # Preserve deleted contributor/delays
                adj_d_start = d_start + buffer_offset
                adj_d_end = d_end + buffer_offset
                preserved_ids = [keystroke_id]
                for i in range(adj_d_start, min(adj_d_end, len(input_val_contributors))):
                    if input_val_contributors[i] >= 0:
                        preserved_ids.append(input_val_contributors[i])
                for i in range(adj_d_start, min(adj_d_end, len(input_val_delays))):
                    preserved_ids.extend(input_val_delays[i])

                input_box.pop()

                # Remove from tracking
                if adj_d_start < len(input_val_contributors):
                    del input_val_contributors[adj_d_start:adj_d_end]
                    del input_val_delays[adj_d_start:adj_d_end]

                # Add preserved IDs as delays
                if adj_d_start < len(input_val_delays):
                    input_val_delays[adj_d_start].extend(preserved_ids)
                else:
                    pending_delays.extend(preserved_ids)

                # Mark tail position after delete as post-correction
                # The next INSERT at this position will have inflated timeDelta (correction overhead)
                tail_pos_after_delete = total_chars_before_word + d_start
                if 0 <= tail_pos_after_delete < len(text):
                    post_correction_positions.add(tail_pos_after_delete)

            # Reset tracking sequence on delete
            tracking_sequence_pos = -1
            # Reset fat-finger tracking on delete
            prev_was_insert = False

        # Delete (range)
        elif action == "-":
            if "," in params:
                start_index, end_index = int(params.split(",")[0]), int(params.split(",")[1])
            else:
                start_index, end_index = int(params), len(input_box)

            d_start = max(0, min(start_index, len(input_box)))
            d_end = max(0, min(end_index, len(input_box)))

            # Preserve deleted contributor/delays
            adj_d_start = d_start + buffer_offset
            adj_d_end = d_end + buffer_offset
            preserved_ids = [keystroke_id]
            for i in range(adj_d_start, min(adj_d_end, len(input_val_contributors))):
                if input_val_contributors[i] >= 0:
                    preserved_ids.append(input_val_contributors[i])
            for i in range(adj_d_start, min(adj_d_end, len(input_val_delays))):
                preserved_ids.extend(input_val_delays[i])

            input_box = input_box[:d_start] + input_box[d_end:]

            # Remove from tracking
            if adj_d_start < len(input_val_contributors):
                del input_val_contributors[adj_d_start:min(adj_d_end, len(input_val_contributors))]
                del input_val_delays[adj_d_start:min(adj_d_end, len(input_val_delays))]

            # Add preserved IDs as delays
            if adj_d_start < len(input_val_delays):
                input_val_delays[adj_d_start].extend(preserved_ids)
            else:
                pending_delays.extend(preserved_ids)

            # Mark tail position after delete as post-correction
            # The next INSERT at this position will have inflated timeDelta (correction overhead)
            tail_pos_after_delete = total_chars_before_word + d_start
            if 0 <= tail_pos_after_delete < len(text):
                post_correction_positions.add(tail_pos_after_delete)

            # Reset tracking sequence on delete
            tracking_sequence_pos = -1
            # Reset fat-finger tracking on delete
            prev_was_insert = False

        # Replace
        elif action == "=":
            key = newline.get(params[-1], params[-1])
            params_rest = params[:-2]
            if "," in params_rest:
                start_index, end_index = int(params_rest.split(",")[0]), int(params_rest.split(",")[1])
            else:
                start_index, end_index = int(params_rest), len(input_box)

            r_start = max(0, min(start_index, len(input_box)))
            r_end = max(0, min(end_index, len(input_box)))

            # Preserve replaced contributor/delays
            adj_r_start = r_start + buffer_offset
            adj_r_end = r_end + buffer_offset
            preserved_ids: list[int] = []
            for i in range(adj_r_start, min(adj_r_end, len(input_val_contributors))):
                if input_val_contributors[i] >= 0:
                    preserved_ids.append(input_val_contributors[i])
            for i in range(adj_r_start, min(adj_r_end, len(input_val_delays))):
                preserved_ids.extend(input_val_delays[i])

            input_box[r_start:r_end] = [key]

            # Update tracking
            if adj_r_start < len(input_val_contributors):
                del input_val_contributors[adj_r_start:min(adj_r_end, len(input_val_contributors))]
                del input_val_delays[adj_r_start:min(adj_r_end, len(input_val_delays))]
            if adj_r_start >= len(input_val_contributors):
                input_val_contributors.append(keystroke_id)
                input_val_delays.append(preserved_ids)
            else:
                input_val_contributors.insert(adj_r_start, keystroke_id)
                input_val_delays.insert(adj_r_start, preserved_ids)

            # Add to character pool with tracking sequence logic
            absolute_pos = total_chars_before_word + r_start

            # Track ALL keystrokes at each position (for post-correction minimum time lookup)
            add_to_position_keystrokes(absolute_pos, keystroke_id, time_delta, key)

            # Mark r_start position as post-correction for REPLACE
            # The REPLACE keystroke itself has inflated timeDelta (correction overhead)
            if 0 <= absolute_pos < len(text):
                post_correction_positions.add(absolute_pos)

            normalized_key = normalize_enter(key)

            # Fat-finger detection for replace (same as insert)
            if (prev_was_insert and prev_insert_key is not None and
                prev_insert_index is not None and prev_insert_keystroke_id >= 0 and
                time_delta <= TRANSPOSITION_THRESHOLD_MS):
                prev_abs_pos = total_chars_before_word + prev_insert_index
                if (0 <= prev_abs_pos < len(text) and
                    normalize_enter(prev_insert_key) != normalize_enter(text[prev_abs_pos]) and
                    normalized_key == normalize_enter(text[prev_abs_pos])):
                    # Fat-finger detected: prev was wrong, current is correct for prev position
                    track_correct_position(prev_abs_pos)
                    add_to_char_pool(text[prev_abs_pos], keystroke_id, prev_abs_pos)
                    prev_time = fat_finger_times.get(prev_insert_keystroke_id, time_deltas[prev_insert_keystroke_id])
                    fat_finger_times[keystroke_id] = prev_time + time_delta

            expected_char = normalize_enter(text[absolute_pos]) if 0 <= absolute_pos < len(text) else ""
            exact_match = 0 <= absolute_pos < len(text) and normalized_key == expected_char
            case_insensitive_match = not exact_match and 0 <= absolute_pos < len(text) and normalized_key.lower() == expected_char.lower()

            if exact_match or case_insensitive_match:
                # Rule 1: Correct position (exact or case-insensitive) - always add
                if exact_match:
                    track_correct_position(absolute_pos)
                add_to_char_pool(key, keystroke_id, absolute_pos)
                tracking_sequence_pos = absolute_pos + 1
            elif 0 <= tracking_sequence_pos < len(text) and normalized_key.lower() == normalize_enter(text[tracking_sequence_pos]).lower():
                # Rule 2: Continues active tracking sequence - add and advance
                track_correct_position(tracking_sequence_pos)
                add_to_char_pool(key, keystroke_id, tracking_sequence_pos)
                tracking_sequence_pos += 1
            else:
                # Rule 3: Try to start new tracking sequence
                match_pos = find_char_in_text(key, 0)
                if match_pos >= 0:
                    tracking_sequence_pos = match_pos + 1
                else:
                    tracking_sequence_pos = -1

            # Update previous keystroke info for fat-finger detection
            prev_insert_key = key
            prev_insert_index = r_start
            prev_insert_keystroke_id = keystroke_id
            prev_was_insert = True

        # Replace (redundant)
        elif action == "~":
            # Just add as delay to first position
            if buffer_offset < len(input_val_delays):
                input_val_delays[buffer_offset].append(keystroke_id)

        # Current text state
        input_string = "".join(input_box)

        # Detect typo
        is_typo = input_string[:len(current_word)] != current_word[:len(input_string)]
        if is_typo and not typo_flag and action not in ["<", "-"]:
            typo_flag = True
            text_typed = "".join(typed_words) + input_string
            typos.append({
                "word_index": word_index,
                "typo_index": len(text_typed) - 1,
                "word": current_word.rstrip(),
            })
        elif not is_typo and typo_flag:
            typo_flag = False

        # Use global tracking sets to prevent double-counting across entire replay
        used_raw_ids = global_used_raw_ids
        used_actual_ids = global_used_actual_ids

        # Word completion
        while (current_word and
               len(input_string) >= len(current_word) and
               input_string[:len(current_word)] == current_word):

            # === Left-to-right raw attribution with transposition adjustment ===
            attribution = [-1] * len(current_word)
            raw_times = [0] * len(current_word)

            # Step 1: Left-to-right attribution - try char_pool first, fall back to contributor
            for i in range(len(current_word)):
                # Calculate absolute position in text for this character
                absolute_pos = total_chars_before_word + i

                # For post-correction positions: use minimum non-fatfinger time from ALL keystrokes at this position
                if absolute_pos in post_correction_positions:
                    all_at_pos = position_keystrokes.get(absolute_pos, [])
                    min_time = float('inf')
                    min_ks_id = -1
                    for ks_id, ks_time_delta, _ in all_at_pos:
                        # Skip fat-fingered keystrokes (they have combined times)
                        # Skip already-used keystrokes
                        if ks_id not in fat_finger_times and ks_id not in used_raw_ids and ks_time_delta < min_time:
                            min_time = ks_time_delta
                            min_ks_id = ks_id
                    if min_ks_id >= 0:
                        used_raw_ids.add(min_ks_id)
                        attribution[i] = min_ks_id
                        raw_times[i] = int(min_time)
                        continue
                    # Fall through to normal logic if no valid keystroke found

                # Check for inversion: if there are keystrokes typed AT this exact position,
                # prefer those over char_pool keystrokes from other positions.
                # This handles inversions where user typed wrong char at correct position.
                # BUT: only use if typed char matches expected char OR adjacent expected char (true inversion).
                keystrokes_at_this_pos = position_keystrokes.get(absolute_pos, [])
                if keystrokes_at_this_pos:
                    expected_char = normalize_enter(current_word[i]).lower()
                    prev_expected = normalize_enter(text[absolute_pos - 1]).lower() if absolute_pos > 0 and absolute_pos - 1 < len(text) else ''
                    next_expected = normalize_enter(text[absolute_pos + 1]).lower() if absolute_pos + 1 < len(text) else ''

                    # Find minimum non-fatfinger time from VALID keystrokes at this position
                    # Valid = typed char matches expected OR adjacent expected (inversion)
                    min_time = float('inf')
                    min_ks_id = -1
                    for ks_id, ks_time_delta, typed_char in keystrokes_at_this_pos:
                        if ks_id in fat_finger_times or ks_id in used_raw_ids:
                            continue

                        # Only use if typed char is valid: matches expected OR adjacent (inversion)
                        normalized_typed = normalize_enter(typed_char).lower()
                        is_valid = normalized_typed == expected_char or normalized_typed == prev_expected or normalized_typed == next_expected

                        if is_valid and ks_time_delta < min_time:
                            min_time = ks_time_delta
                            min_ks_id = ks_id
                    if min_ks_id >= 0:
                        used_raw_ids.add(min_ks_id)
                        attribution[i] = min_ks_id
                        raw_times[i] = int(min_time)
                        continue

                # Try char_pool - find earliest unused keystroke that typed expected char
                expected_char = current_word[i]
                normalized_expected = normalize_enter(expected_char).lower()
                pool = char_pool.get(normalized_expected, [])

                found_in_pool = False
                # Find earliest unused keystroke from pool (with position window check)
                for ks_id, typed_at_pos in pool:
                    # Check position window: keystroke must have been typed within ATTRIBUTION_WINDOW of target
                    if ks_id not in used_raw_ids and abs(typed_at_pos - absolute_pos) <= ATTRIBUTION_WINDOW:
                        used_raw_ids.add(ks_id)
                        attribution[i] = ks_id
                        # Use fat-finger combined time if available, otherwise use timeDelta
                        raw_times[i] = fat_finger_times.get(ks_id, time_deltas[ks_id])
                        found_in_pool = True
                        break

                # Fall back to contributor timing if char_pool had no match
                if not found_in_pool:
                    adj_i = i + buffer_offset
                    contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                    if contributor_id >= 0 and contributor_id not in used_raw_ids:
                        used_raw_ids.add(contributor_id)
                        attribution[i] = contributor_id
                        raw_times[i] = time_deltas[contributor_id]

            # Step 2: Inversion adjustment (process backwards)
            for i in range(len(current_word) - 1, 0, -1):
                ks_prev = attribution[i - 1]
                ks_curr = attribution[i]
                if ks_prev >= 0 and ks_curr >= 0 and ks_prev > ks_curr:
                    # Inversion: pos-1's keystroke was typed AFTER pos's
                    gap = sum(time_deltas[ks_curr + 1:ks_prev + 1])
                    if gap <= TRANSPOSITION_THRESHOLD_MS:
                        raw_times[i - 1] += raw_times[i]
                        raw_times[i] = 0

            # Add raw times to character times
            raw_character_times.extend(raw_times)

            # Calculate actual WPM times using post-hoc attribution (contributor + delays)
            for i in range(len(current_word)):
                adj_i = i + buffer_offset
                contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                delay_ids = input_val_delays[adj_i] if adj_i < len(input_val_delays) else []

                actual_time = 0
                if contributor_id >= 0 and contributor_id not in used_actual_ids:
                    used_actual_ids.add(contributor_id)
                    actual_time += time_deltas[contributor_id]
                for delay_id in delay_ids:
                    if delay_id not in used_actual_ids:
                        used_actual_ids.add(delay_id)
                        actual_time += time_deltas[delay_id]
                wpm_character_times.append(actual_time)

            # Reset for next word
            input_string = input_string[len(current_word):]
            input_box = list(input_string)
            buffer_offset += len(current_word)
            typed_words.append(current_word)
            total_chars_before_word += len(current_word)
            word_index += 1
            current_word = words[word_index] if word_index < len(words) else ""

            # Reset tracking sequence after word completion
            tracking_sequence_pos = -1

    # Convert character times to cumulative WPM
    keystroke_wpm = get_keystroke_wpm(wpm_character_times)
    keystroke_wpm_raw = get_keystroke_wpm(raw_character_times)

    return {
        "keystroke_wpm": keystroke_wpm,
        "keystroke_wpm_raw": keystroke_wpm_raw,
        "typos": typos,
    }


def get_keystroke_wpm(delays: list[int], adjusted: bool = False):
    """
    Returns a list of WPM over keystrokes given a list of ms delays.
    adjusted = True will always eliminate the first delay.
    """
    if not delays:
        return []

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
