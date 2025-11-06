"""Temporary file until raw speed is solidified."""
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Union


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


KeystrokeAction = Union[KeystrokeInsert, KeystrokeDelete, KeystrokeReplace]


@dataclass
class Keystroke:
    action: KeystrokeAction
    time: int
    timeDelta: int


@dataclass
class KeystrokeData:
    text: str
    keystrokes: List[Keystroke]
    isStickyStart: bool


@dataclass
class KeystrokeTiming:
    id: int
    timeDelta: int


@dataclass
class GraphDataPoint:
    charIndex: int
    wordIndex: int
    initialKeystrokeId: int
    wpm: Optional[float] = None
    raw: Optional[float] = None
    time: float = 0.0


@dataclass
class ProcessResult:
    keystrokesWpmGraphData: List[GraphDataPoint]
    rawCharacterTimes: List[float]
    wpmCharacterTimes: List[float]


def split_words(text: str) -> List[str]:
    """Split text into words, handling newlines and spaces appropriately."""
    text_processed = text.replace("⏎ ", "⏎").replace("\r\n", "⏎").replace("\n", "⏎")
    words = text_processed.split(" ")

    for i in range(len(words) - 1):
        w = words[i]
        if not w.endswith("⏎"):
            words[i] += " "

    return words


def calculate_wpm(chars: int, time_ms: float) -> float:
    """Calculate WPM given characters typed and time in milliseconds."""
    if time_ms <= 0:
        return 0.0
    return (chars / 5) * (60000 / time_ms)


def process_keystroke_data(
    keystroke_data: KeystrokeData,
    is_multiplayer: bool = False,
    reaction_time: float = 0
) -> ProcessResult:
    """Process keystroke data to calculate typing metrics and WPM."""
    keystrokes = keystroke_data.keystrokes
    text = keystroke_data.text.replace("\r\n", "\n")
    words = split_words(text)

    matched_lengths: Dict[int, int] = {}
    raw_character_times: List[float] = []
    wpm_character_times: List[float] = []

    # Track which character positions already have an initial keystroke assigned
    initial_keystroke_assigned = [False] * len(text)
    char_initial_keystroke_ids = [-1] * len(text)

    keystrokes_wpm_graph_data: List[GraphDataPoint] = []

    # State
    input_val = ""
    word_index = 0

    words_char_inserts_graph: Dict[int, List[List[KeystrokeTiming]]] = {}

    def get_absolute_position(relative_position: int) -> int:
        """Get absolute character position within the entire text."""
        chars_before_current_word = sum(len(word) for word in words[:word_index])
        return chars_before_current_word + relative_position

    # ---------- MAIN LOOP OVER KEYSTROKES ----------
    for keystroke_id, keystroke in enumerate(keystrokes):
        action = keystroke.action
        time = keystroke.time
        time_delta = keystroke.timeDelta

        current_word = words[word_index] if word_index < len(words) else ""

        if isinstance(action, KeystrokeInsert):
            # Insert
            i = max(0, min(action.i, len(input_val)))
            input_val = input_val[:i] + action.key + input_val[i:]

            # Track initial keystroke assignment for characters
            absolute_position = get_absolute_position(action.i)
            if (0 <= absolute_position < len(initial_keystroke_assigned) and
                not initial_keystroke_assigned[absolute_position]):
                initial_keystroke_assigned[absolute_position] = True
                char_initial_keystroke_ids[absolute_position] = keystroke_id

        elif isinstance(action, KeystrokeReplace):
            # Replace
            r_start = max(0, min(action.rStart, len(input_val)))
            r_end = max(0, min(action.rEnd, len(input_val)))
            if 0 <= r_start <= r_end <= len(input_val):
                input_val = input_val[:r_start] + action.key + input_val[r_end:]

            # Track initial keystroke assignment
            absolute_position = get_absolute_position(action.rStart)
            if (0 <= absolute_position < len(initial_keystroke_assigned) and
                not initial_keystroke_assigned[absolute_position]):
                initial_keystroke_assigned[absolute_position] = True
                char_initial_keystroke_ids[absolute_position] = keystroke_id

        elif isinstance(action, KeystrokeDelete):
            # Delete
            d_start = max(0, min(action.dStart, len(input_val)))
            d_end = max(0, min(action.dEnd, len(input_val)))
            input_val = input_val[:d_start] + input_val[d_end:]

        # ---------- UPDATE CHARACTER TIMINGS ----------
        LOOKAHEAD = 4
        max_word = min(word_index + LOOKAHEAD, len(words))

        for w in range(word_index, max_word):
            if w >= len(words):
                break

            temp_current_word = words[w]
            if len(temp_current_word) == 0:
                continue

            # Initialize the arrays if they don't exist
            if w not in words_char_inserts_graph:
                words_char_inserts_graph[w] = [[] for _ in range(len(temp_current_word))]

            # Recalculate matched lengths for non-chronological inserts
            if not (isinstance(action, KeystrokeInsert) and action.i >= len(input_val) - 1):
                new_matched_length = 0
                j = 0
                for i in range(len(input_val)):
                    if j >= len(temp_current_word):
                        break
                    if input_val[i] == temp_current_word[j]:
                        new_matched_length += 1
                        j += 1
                matched_lengths[w] = new_matched_length

            if hasattr(action, 'key') and action.key:
                needed_index = matched_lengths.get(w, 0)
                if needed_index < len(temp_current_word):
                    if action.key == temp_current_word[needed_index]:
                        words_char_inserts_graph[w][needed_index].append(
                            KeystrokeTiming(id=keystroke_id, timeDelta=time_delta)
                        )
                        matched_lengths[w] = needed_index + 1

        # ---------- WORD COMPLETION PROCESSING ----------
        while (len(current_word) > 0 and
               input_val[:len(current_word)] == current_word and
               word_index < len(words)):

            def pick_min_unique_timing(timings: List[KeystrokeTiming], used: Set[int]) -> float:
                """Pick minimum timeDelta for each character (for raw WPM)."""
                available = [t for t in timings if t.id not in used]
                if not available:
                    return 0.0
                min_timing = min(available, key=lambda x: x.timeDelta)
                used.add(min_timing.id)
                return min_timing.timeDelta

            def sum_unique_times_for_character(
                insert_timings: List[KeystrokeTiming],
                used: Set[int]
            ) -> float:
                """Sum all unique timings for each character (for actual WPM)."""
                total = 0.0
                for timing in insert_timings:
                    if timing.id not in used:
                        used.add(timing.id)
                        total += timing.timeDelta
                return total

            # Calculate raw times per char in word
            used_raw_ids: Set[int] = set()
            raw_times_for_word = [
                pick_min_unique_timing(timings, used_raw_ids)
                for timings in words_char_inserts_graph[word_index]
            ]
            raw_character_times.extend(raw_times_for_word)

            # Calculate actual times per char in word
            used_actual_ids: Set[int] = set()
            actual_times_for_word = [
                sum_unique_times_for_character(insert_timings, used_actual_ids)
                for insert_timings in words_char_inserts_graph[word_index]
            ]

            chars_before = len(wpm_character_times) if wpm_character_times else 1
            wpm_character_times.extend(actual_times_for_word)

            # Generate keystroke graph data
            total_chars_before_curr_word = sum(len(word) for word in words[:word_index])

            for i in range(chars_before, len(wpm_character_times)):
                keystroke_total_time = sum(wpm_character_times[:i + 1])

                if is_multiplayer and reaction_time > 0:
                    keystroke_total_time += reaction_time

                absolute_char_index = total_chars_before_curr_word + (i - chars_before)
                char_initial_keystroke_id = (
                    char_initial_keystroke_ids[absolute_char_index]
                    if 0 <= absolute_char_index < len(char_initial_keystroke_ids)
                    else -1
                )

                raw_total_time = sum(raw_character_times[:i + 1])
                if is_multiplayer and reaction_time > 0:
                    raw_total_time += reaction_time

                keystrokes_wpm_graph_data.append(
                    GraphDataPoint(
                        charIndex=i,
                        wordIndex=word_index,
                        initialKeystrokeId=char_initial_keystroke_id,
                        raw=calculate_wpm(i + (1 if is_multiplayer else 0), raw_total_time),
                        wpm=calculate_wpm(i + (1 if is_multiplayer else 0), keystroke_total_time),
                        time=keystroke_total_time
                    )
                )

            # Clean up for next word
            input_val = input_val[len(current_word):]
            if not input_val:
                words_char_inserts_graph.clear()
                matched_lengths.clear()
            else:
                if word_index in words_char_inserts_graph:
                    del words_char_inserts_graph[word_index]
                if word_index in matched_lengths:
                    del matched_lengths[word_index]

            word_index += 1
            current_word = words[word_index] if word_index < len(words) else ""

    return ProcessResult(
        keystrokesWpmGraphData=keystrokes_wpm_graph_data,
        rawCharacterTimes=raw_character_times,
        wpmCharacterTimes=wpm_character_times
    )


def get_keystroke_wpm_raw(raw_keystroke_data: list[dict], adjusted: bool = False):
    """
    Returns a list of WPM over keystrokes given a list of keystrokes.
    adjusted = True will always eliminate the first delay.
    """
    from utils.keylogs import get_keystroke_wpm
    
    keystroke_data = KeystrokeData(
        text=raw_keystroke_data["text"],
        isStickyStart=raw_keystroke_data["isStickyStart"],
        keystrokes=[],
    )

    for keystroke in raw_keystroke_data["keystrokes"]:
        action_class = None
        action = keystroke["action"]

        if "i" in action:
            action_class = KeystrokeInsert(
                i=action["i"],
                key=action["key"],
            )
        elif "rStart" in action:
            action_class = KeystrokeReplace(
                rStart=action["rStart"],
                rEnd=action["rEnd"],
                key=action["key"],
            )
        elif "dStart" in action:
            action_class = KeystrokeDelete(
                dStart=action["dStart"],
                dEnd=action["dEnd"],
            )
        keystroke_data.keystrokes.append(Keystroke(
            action=action_class,
            time=keystroke["time"],
            timeDelta=keystroke["timeDelta"],
        ))

    processed_data = process_keystroke_data(keystroke_data)
    delays = processed_data.rawCharacterTimes

    return get_keystroke_wpm(delays)
