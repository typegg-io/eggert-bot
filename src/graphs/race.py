from collections import defaultdict

import numpy as np
from matplotlib.axes import Axes

from graphs.core import plt, apply_theme, generate_file_name, filter_palette
from utils.keystrokes import Typo


def render(
    keystroke_wpm: list[float],
    keystroke_wpm_raw: list[float],
    typos: list[Typo],
    username: str,
    title: str,
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    keystrokes = np.arange(1, len(keystroke_wpm) + 1)
    raw_keystrokes = np.arange(1, len(keystroke_wpm_raw) + 1)
    ax.plot(raw_keystrokes, keystroke_wpm_raw, label="Raw Speed")
    ax.plot(keystrokes, keystroke_wpm, label=username)

    word_counts = defaultdict(int)
    for typo in typos:
        word_counts[typo.word_index] += 1

    typo_count = 0
    word_indexes = {}
    max_legend_typos = 16
    quote_length = len(keystroke_wpm)
    marker_size = 7
    if quote_length >= 500:
        marker_size = 4
    if quote_length >= 1000:
        marker_size = 2

    for typo in typos:
        word_index = typo.word_index
        index = typo.typo_index
        word = typo.word
        last_index = word_indexes.get(word_index, -1)
        if index <= last_index:
            continue

        word_indexes[word_index] = index
        wpm = keystroke_wpm[max(0, index - 1)]

        label = None
        if last_index == -1:
            typo_count += 1
            if typo_count <= max_legend_typos:
                label = f"{typo_count}. {word}"
                if word_counts[word_index] > 1:
                    label += f" (x{word_counts[word_index]})"

        ax.plot(
            index, wpm, marker="x", color=theme["crosses"], zorder=777,
            markersize=marker_size, markeredgewidth=1.5, label=label
        )

    if typo_count > max_legend_typos:
        ax.plot(
            [], [], marker="x", color=theme["crosses"], markersize=marker_size,
            markeredgewidth=1.5, label=f"{typo_count - max_legend_typos} more typos..."
        )

    apply_padding(ax, [keystroke_wpm, keystroke_wpm_raw])
    ax.set_xlabel("Keystrokes")
    ax.set_ylabel("WPM")
    ax.set_title(title)

    apply_theme(ax, theme, themed_line=1)

    file_name = generate_file_name("race")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_padding(ax: Axes, keystroke_wpms: list[list[float]]):
    """Set Y-axis limits to reasonable WPM bounds with padding."""
    starts = []
    rest = []
    max_wpm = float("-inf")
    min_wpm = float("inf")

    for keystroke_wpm in keystroke_wpms:
        valid_wpm = [w for w in keystroke_wpm if w < float("inf")]

        if not valid_wpm:
            continue

        starts.extend(valid_wpm[:9])
        rest.extend(valid_wpm[9:])

        max_wpm = max(max(valid_wpm), max_wpm)
        min_wpm = min(min(valid_wpm), min_wpm)

    if rest:
        max_start, max_rest = max(starts), max(rest)
        min_start, min_rest = min(starts), min(rest)

        if max_start > max_rest:
            max_wpm = max_rest
        if min_start < min_rest:
            min_wpm = min_rest

    padding = 0.1 * (max_wpm - min_wpm)
    ax.set_ylim(min_wpm - padding, max_wpm + padding)
