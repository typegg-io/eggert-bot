import numpy as np

from graphs.core import plt, apply_theme, generate_file_name, filter_palette
from graphs.race import apply_padding


def render(
    race_data: list[dict],
    title: str,
    theme: dict,
    themed_line: int = 0,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    keystroke_wpms = []
    racer_count = len(race_data)

    for i, race in enumerate(race_data):
        username = race["username"]
        keystroke_wpm = race["keystroke_wpm"]
        keystroke_wpms.append(keystroke_wpm)
        keystrokes = np.arange(1, len(keystroke_wpm) + 1)

        ax.plot(keystrokes, keystroke_wpm, label=username, zorder=racer_count - i)

    apply_padding(ax, keystroke_wpms)
    ax.set_xlabel("Keystrokes")
    ax.set_ylabel("WPM")
    ax.set_title(title)

    apply_theme(ax, theme, themed_line=themed_line)

    file_name = generate_file_name("matchgraph")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
