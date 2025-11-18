from collections import defaultdict

import numpy as np
from matplotlib.axes import Axes

from graphs.core import plt, apply_theme, generate_file_name


def render(
    keystroke_wpm: list[float],
    keystroke_wpm_raw: list[float],
    typos: list[dict],
    username: str,
    title: str,
    theme: dict,
):
    fig, ax = plt.subplots()

    keystrokes = np.arange(1, len(keystroke_wpm) + 1)
    raw_keystrokes = np.arange(1, len(keystroke_wpm_raw) + 1)
    ax.plot(raw_keystrokes, keystroke_wpm_raw, label="Raw Speed")
    ax.plot(keystrokes, keystroke_wpm, label=username)

    word_counts = defaultdict(int)
    for typo in typos:
        word_counts[typo["word_index"]] += 1

    typo_count = 0
    word_indexes = {}

    for typo in typos:
        word_index = typo["word_index"]
        index = typo["typo_index"]
        word = typo["word"]
        last_index = word_indexes.get(word_index, -1)
        if index <= last_index:
            continue

        word_indexes[word_index] = index
        wpm = keystroke_wpm[max(0, index - 1)]

        label = None
        if last_index == -1:
            typo_count += 1
            label = f"{typo_count}. {word}"
            if word_counts[word_index] > 1:
                label += f" (x{word_counts[word_index]})"

        ax.plot(
            index, wpm, marker="x", color="red", zorder=777,
            markersize=7, markeredgewidth=1.5, label=label
        )

    apply_padding(ax, keystroke_wpm + keystroke_wpm_raw)
    ax.set_xlabel("Keystrokes")
    ax.set_ylabel("WPM")
    ax.set_title(title)

    apply_theme(ax, theme, themed_line=1)

    file_name = generate_file_name("race")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_padding(ax: Axes, keystroke_wpm: list[float]):
    """Set Y-axis limits to reasonable WPM bounds with padding."""
    valid_wpm = [w for w in keystroke_wpm if w < float("inf")]
    if not valid_wpm:
        return

    min_wpm, max_wpm = min(valid_wpm), max(valid_wpm)
    starts, remaining = valid_wpm[:9], valid_wpm[9:]

    if remaining:
        max_start, max_rest = max(starts), max(remaining)
        min_start, min_rest = min(starts), min(remaining)

        if max_start > max_rest:
            max_wpm = max_rest * 1.1
        if min_start < min_rest:
            min_wpm = min_rest * 0.9

    padding = 0.1 * (max_wpm - min_wpm)
    ax.set_ylim(min_wpm - padding, max_wpm + padding)
