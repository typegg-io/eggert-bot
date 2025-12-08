import numpy as np

from graphs.core import plt, apply_theme, generate_file_name


def render(
    score_list: list[dict],
    title: str,
    theme: dict,
    themed_line: int = 0,
):
    fig, ax = plt.subplots()
    keystroke_wpms = []

    for score in score_list:
        keystroke_wpm = score["keystroke_wpm"]
        keystroke_wpms.append(keystroke_wpm)

        keystrokes = np.arange(1, len(keystroke_wpm) + 1)
        ax.plot(keystrokes, keystroke_wpm, label=score["username"])

    apply_padding(ax, keystroke_wpms)
    ax.set_xlabel("Keystrokes")
    ax.set_ylabel("WPM")
    ax.set_title(title, fontsize=10)

    apply_theme(ax, theme, themed_line=themed_line)

    file_name = generate_file_name("daily")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_padding(ax, keystroke_wpms: list[list[float]]):
    """Set Y-axis limits to reasonable WPM bounds with padding."""
    all_starts = []
    all_remaining = []
    min_wpm = float("inf")
    max_wpm = 0

    for keystroke_wpm in keystroke_wpms:
        valid_wpm = [w for w in keystroke_wpm if w < float("inf")]

        if not valid_wpm:
            continue

        min_wpm = min(min(valid_wpm), min_wpm)
        max_wpm = max(max(valid_wpm), max_wpm)
        starts, remaining = valid_wpm[:9], valid_wpm[9:]

        all_starts += starts
        all_remaining += remaining

    max_start, max_rest = max(all_starts), max(all_remaining)
    min_start, min_rest = min(all_starts), min(all_remaining)

    if max_start > max_rest:
        max_wpm = max_rest * 1.1
    if min_start < min_rest:
        min_wpm = min_rest * 0.9

    ax.set_ylim(min_wpm, max_wpm)
