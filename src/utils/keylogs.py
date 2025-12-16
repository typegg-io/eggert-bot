import re
from typing import Optional


FAT_FINGER_THRESHOLD_MS = 7


def get_keystroke_data(keystroke_data: dict):
    """
    Parses keystroke data to calculate per-character WPM and raw WPM using
    post-hoc attribution algorithm (matching frontend/backend implementations).

    WPM: Uses contributor + delays (accounts for corrections)
    Raw WPM: Uses absolute position matching + minimum picking + fat-finger detection
    """
    event_data = None
    newline = {"⏎": "\n"}

    if isinstance(keystroke_data, dict):
        keystrokes = keystroke_data["keystrokes"]
        text = keystroke_data["text"].replace("\r\n", "\n")
    else:
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

    # Raw WPM attribution: absolute text position -> list of keystroke IDs
    raw_attributions: dict[int, list[int]] = {}
    fat_finger_times: dict[int, int] = {}  # keystrokeId -> adjusted time

    # Character timing results
    wpm_character_times: list[float] = []
    raw_character_times: list[float] = []

    # State
    input_box: list[str] = []
    typed_words: list[str] = []
    word_index = 0
    total_chars_before_word = 0
    prev_input = ""

    def add_raw_attribution(absolute_pos: int, keystroke_id: int):
        """Add a keystroke as a candidate for raw WPM at an absolute position."""
        if absolute_pos < 0 or absolute_pos >= len(text):
            return
        if absolute_pos not in raw_attributions:
            raw_attributions[absolute_pos] = []
        if keystroke_id not in raw_attributions[absolute_pos]:
            raw_attributions[absolute_pos].append(keystroke_id)

    def get_raw_time(keystroke_id: int, time_deltas: list[int]) -> int:
        """Get raw time for a keystroke (uses fat-finger adjusted time if available)."""
        return fat_finger_times.get(keystroke_id, time_deltas[keystroke_id])

    if event_data:
        # CODEC_VERSION 1
        events = re.split(r"\|(?=\d)", event_data)
        event_re = re.compile(r"^(\d+)(.)(.*)$")

        time_deltas: list[int] = []
        prev_key: Optional[str] = None
        prev_index: Optional[int] = None
        prev_input_len = 0
        prev_was_insert = False

        for keystroke_id, event in enumerate(events):
            match = event_re.match(event)
            if not match:
                continue
            time_delta_str, action, params = match.groups()
            time_delta = int(time_delta_str)
            time_deltas.append(time_delta)

            current_word = words[word_index] if word_index < len(words) else ""
            key: Optional[str] = None
            index: Optional[int] = None

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
                index = r_start

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

            # Replace (redundant)
            elif action == "~":
                # Just add as delay to first position
                if buffer_offset < len(input_val_delays):
                    input_val_delays[buffer_offset].append(keystroke_id)

            is_insert_action = action in ["+", ">"]

            # Raw WPM attribution
            if key is not None and index is not None:
                absolute_pos = total_chars_before_word + index

                # Fat-finger detection
                if (keystroke_id > 0 and time_delta <= FAT_FINGER_THRESHOLD_MS and
                    prev_was_insert and prev_key is not None and prev_index is not None and
                    prev_index <= prev_input_len):
                    prev_abs_pos = total_chars_before_word + prev_index
                    if (0 <= prev_abs_pos < len(text) and
                        prev_key != text[prev_abs_pos] and
                        key == text[prev_abs_pos]):
                        # Fat-finger detected
                        prev_time = fat_finger_times.get(keystroke_id - 1, time_deltas[keystroke_id - 1])
                        fat_finger_times[keystroke_id] = prev_time + time_delta
                        add_raw_attribution(prev_abs_pos, keystroke_id)

                # Normal attribution
                if 0 <= absolute_pos < len(text) and key == text[absolute_pos]:
                    add_raw_attribution(absolute_pos, keystroke_id)

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

            # Track used keystroke IDs across all words completing in this batch
            # This prevents double-counting when a single keystroke triggers multiple word completions
            used_raw_ids = set()
            used_actual_ids = set()

            # Word completion
            while (current_word and
                   len(input_string) >= len(current_word) and
                   input_string[:len(current_word)] == current_word):

                # Calculate times for this word using post-hoc attribution
                for i in range(len(current_word)):
                    adj_i = i + buffer_offset
                    contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                    delay_ids = input_val_delays[adj_i] if adj_i < len(input_val_delays) else []
                    absolute_pos = total_chars_before_word + i

                    # Add contributor to raw attributions
                    if contributor_id >= 0:
                        add_raw_attribution(absolute_pos, contributor_id)

                    # Raw WPM: minimum picking
                    raw_time = 0
                    attributed_ids = raw_attributions.get(absolute_pos, [])
                    min_raw_time = float("inf")
                    min_raw_id = -1
                    for kid in attributed_ids:
                        if kid not in used_raw_ids:
                            t = get_raw_time(kid, time_deltas)
                            if t < min_raw_time:
                                min_raw_time = t
                                min_raw_id = kid
                    if min_raw_id >= 0:
                        used_raw_ids.add(min_raw_id)
                        raw_time = int(min_raw_time)
                    raw_character_times.append(raw_time)

                    # Actual WPM: contributor + delays
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

            prev_key = key
            prev_index = index
            prev_input_len = len(input_box)  # After word completion
            prev_was_insert = is_insert_action

    else:
        # Legacy keystroke data format
        time_deltas = [ks["timeDelta"] for ks in keystrokes]
        prev_key: Optional[str] = None
        prev_index: Optional[int] = None
        prev_input_len = 0
        prev_was_insert = False

        for keystroke_id, keystroke in enumerate(keystrokes):
            action = keystroke["action"]
            time_delta = keystroke["timeDelta"]
            current_word = words[word_index] if word_index < len(words) else ""
            key: Optional[str] = None
            index: Optional[int] = None

            if "i" in action:
                # Insert
                key = action.get("key", "")
                if key == "⏎":
                    key = "\n"
                index = max(0, min(action["i"], len(input_box)))
                input_box.insert(index, key)

                # Track contributor
                adjusted_i = index + buffer_offset
                if adjusted_i >= len(input_val_contributors):
                    input_val_contributors.append(keystroke_id)
                    input_val_delays.append(pending_delays[:] if pending_delays else [])
                else:
                    input_val_contributors.insert(adjusted_i, keystroke_id)
                    input_val_delays.insert(adjusted_i, pending_delays[:] if pending_delays else [])
                pending_delays = []

            elif "rStart" in action:
                # Replace
                key = action.get("key", "")
                if key == "⏎":
                    key = "\n"
                r_start = max(0, min(action["rStart"], len(input_box)))
                r_end = max(0, min(action["rEnd"], len(input_box)))
                index = r_start

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

            elif "dStart" in action:
                # Delete
                d_start = max(0, min(action["dStart"], len(input_box)))
                d_end = max(0, min(action["dEnd"], len(input_box)))
                if d_start > d_end:
                    d_start, d_end = d_end, d_start

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

            # Track if this action is an insert (for fat-finger detection on next keystroke)
            is_insert_action = "i" in action

            # Raw WPM attribution
            if key is not None and index is not None:
                absolute_pos = total_chars_before_word + index

                # Fat-finger detection (only if previous action was insert)
                # Skip if word boundary crossed (prev_index > prev_input_len means word completion cleared buffer)
                if (keystroke_id > 0 and time_delta <= FAT_FINGER_THRESHOLD_MS and
                    prev_was_insert and prev_key is not None and prev_index is not None and
                    prev_index <= prev_input_len):
                    prev_abs_pos = total_chars_before_word + prev_index
                    if (0 <= prev_abs_pos < len(text) and
                        prev_key != text[prev_abs_pos] and
                        key == text[prev_abs_pos]):
                        # Fat-finger detected
                        prev_time = fat_finger_times.get(keystroke_id - 1, time_deltas[keystroke_id - 1])
                        fat_finger_times[keystroke_id] = prev_time + time_delta
                        add_raw_attribution(prev_abs_pos, keystroke_id)

                # Normal attribution
                if 0 <= absolute_pos < len(text) and key == text[absolute_pos]:
                    add_raw_attribution(absolute_pos, keystroke_id)

            # Current text state
            input_string = "".join(input_box)

            # Detect typo
            is_typo = input_string[:len(current_word)] != current_word[:len(input_string)]
            if is_typo and not typo_flag and "dStart" not in action:
                typo_flag = True
                text_typed = "".join(typed_words) + input_string
                typos.append({
                    "word_index": word_index,
                    "typo_index": len(text_typed) - 1,
                    "word": current_word.rstrip(),
                })
            elif not is_typo and typo_flag:
                typo_flag = False

            # Track used keystroke IDs across all words completing in this batch
            # This prevents double-counting when a single keystroke triggers multiple word completions
            used_raw_ids = set()
            used_actual_ids = set()

            # Word completion
            while (current_word and
                   len(input_string) >= len(current_word) and
                   input_string[:len(current_word)] == current_word):

                # Calculate times for this word using post-hoc attribution
                for i in range(len(current_word)):
                    adj_i = i + buffer_offset
                    contributor_id = input_val_contributors[adj_i] if adj_i < len(input_val_contributors) else -1
                    delay_ids = input_val_delays[adj_i] if adj_i < len(input_val_delays) else []
                    absolute_pos = total_chars_before_word + i

                    # Add contributor to raw attributions
                    if contributor_id >= 0:
                        add_raw_attribution(absolute_pos, contributor_id)

                    # Raw WPM: minimum picking
                    raw_time = 0
                    attributed_ids = raw_attributions.get(absolute_pos, [])
                    min_raw_time = float("inf")
                    min_raw_id = -1
                    for kid in attributed_ids:
                        if kid not in used_raw_ids:
                            t = get_raw_time(kid, time_deltas)
                            if t < min_raw_time:
                                min_raw_time = t
                                min_raw_id = kid
                    if min_raw_id >= 0:
                        used_raw_ids.add(min_raw_id)
                        raw_time = int(min_raw_time)
                    raw_character_times.append(raw_time)

                    # Actual WPM: contributor + delays
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

            prev_key = key
            prev_index = index
            prev_input_len = len(input_box)  # After word completion
            prev_was_insert = is_insert_action

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
