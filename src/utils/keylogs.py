import re

from utils.keystrokes import get_keystroke_wpm_raw


def get_keystroke_data(keystroke_data: dict):
    """Parses keystroke data to calculate per-character delays and identify typos."""
    event_data = None
    if isinstance(keystroke_data, dict):
        keystrokes = keystroke_data["keystrokes"]
        text = keystroke_data["text"].replace("\r\n", "\n")
    else:
        codec_version, text, sticky_start, event_data = keystroke_data

    words = re.findall(r".*?(?: |\n|$)", text)[:-1]

    input_box = []
    typed_words = []
    current_word_index = 0
    current_duration = 0

    delays = [0] * len(text)
    typos = []
    typo_flag = False

    if event_data:
        events = re.split(r"\|(?=\d)", event_data)
        event_re = re.compile(r"^(\d+)(.)(.*)$")

        for event in events:
            time_delta, action, params = event_re.match(event).groups()
            time_delta = int(time_delta)

            # Insert (append)
            if action == "+":
                input_box.append(params)

            # Insert (at pos)
            elif action == ">":
                char = params[-1]
                index = int(params[:-2])

                if index >= len(input_box):
                    input_box.extend([""] * (index + 1 - len(input_box)))

                input_box[index] = char

            # Delete (backspace)
            elif action == "<":
                input_box.pop()

            # Delete
            elif action == "-":
                if len(params) == 1:  # from end
                    start_index, end_index = params, len(input_box)
                else:  # range
                    start_index, end_index = params.split(",")
                input_box = input_box[:int(start_index)] + input_box[int(end_index):]

            # Replace
            elif action == "=":
                char = params[-1]
                params = params[:-2]
                if len(params) == 1:  # from end
                    start_index, end_index = params, len(input_box)
                else:  # range
                    start_index, end_index = params.split(",")
                input_box[int(start_index):int(end_index)] = char

            # Replace (redundant)
            elif action == "~":
                pass

            # Accumulate timing
            current_duration += time_delta

            # Current text state
            input_string = "".join(input_box)
            current_word = words[current_word_index]
            text_typed = "".join(typed_words) + input_string
            current_index = min(len(text_typed) - 1, len(text) - 1)

            # Detect typo
            is_typo = input_string[:len(current_word)] != current_word[:len(input_string)]
            if is_typo and not typo_flag and "dStart" not in action:
                typo_flag = True
                typos.append({
                    "word_index": current_word_index,
                    "typo_index": len(text_typed) - 1,
                    "word": current_word.rstrip(),
                })
            elif not is_typo and typo_flag:
                typo_flag = False

            # Update delay when text is correct
            if text_typed and text_typed[:len(text)] == text[:current_index + 1]:
                if delays[current_index] == 0:
                    delays[current_index] = current_duration
                    current_duration = 0

            # Update completed words and input box
            if input_string[:len(current_word)] == current_word:
                typed_words.append(current_word)
                current_word_index += 1
                previous_word = words[current_word_index - 1]
                input_box = list(input_string[len(previous_word):])
    else:

        for keystroke in keystrokes:
            action = keystroke["action"]
            key = action.get("key")

            if key == "⏎":
                key = "\n"

            # Apply keystroke action
            if "i" in action:  # Insert
                input_box.insert(action["i"], key)
            elif "rStart" in action:  # Replace
                input_box[action["rStart"]:action["rEnd"]] = key
            elif "dStart" in action:  # Delete
                input_box = input_box[:action["dStart"]] + input_box[action["dEnd"]:]

            # Accumulate timing
            current_duration += keystroke["timeDelta"]

            # Current text state
            input_string = "".join(input_box)
            current_word = words[current_word_index]
            text_typed = "".join(typed_words) + input_string
            current_index = min(len(text_typed) - 1, len(text) - 1)

            # Detect typo
            is_typo = input_string[:len(current_word)] != current_word[:len(input_string)]
            if is_typo and not typo_flag and "dStart" not in action:
                typo_flag = True
                typos.append({
                    "word_index": current_word_index,
                    "typo_index": len(text_typed) - 1,
                    "word": current_word.rstrip(),
                })
            elif not is_typo and typo_flag:
                typo_flag = False

            # Update delay when text is correct
            if text_typed and text_typed[:len(text)] == text[:current_index + 1]:
                if delays[current_index] == 0:
                    delays[current_index] = current_duration
                    current_duration = 0

            # Update completed words and input box
            if input_string[:len(current_word)] == current_word:
                typed_words.append(current_word)
                current_word_index += 1
                previous_word = words[current_word_index - 1]
                input_box = list(input_string[len(previous_word):])

    keystroke_wpm = get_keystroke_wpm(delays)

    return {
        "keystroke_wpm": keystroke_wpm,
        # "keystroke_wpm_raw": get_keystroke_wpm_raw(keystroke_data),
        "keystroke_wpm_raw": [],
        "typos": typos,
    }


def get_keystroke_wpm(delays: list[int], adjusted: bool = False):
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
