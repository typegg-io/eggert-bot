from dataclasses import dataclass
from typing import List

from graphs.core import plt, apply_theme, generate_file_name, filter_palette, apply_log_ticks
from utils.strings import format_big_number


@dataclass
class UserEnduranceData:
    username: str
    wpm_values: List[float]
    length_values: List[int]


def render(
    first_username: str,
    data: List[UserEnduranceData],
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    themed_line = 0
    max_length = 0

    for line_index, endurance_data in enumerate(data[::-1]):
        username = endurance_data.username
        wpm_values = endurance_data.wpm_values
        length_values = endurance_data.length_values

        step_wpm = []
        step_length = []

        for j in range(len(wpm_values) - 1):
            step_wpm.extend([wpm_values[j], wpm_values[j + 1]])
            step_length.extend([length_values[j], length_values[j]])

        step_wpm.append(wpm_values[-1])
        step_length.append(length_values[-1])

        if username == first_username:
            themed_line = line_index

        ax.plot(step_length, step_wpm, label=username)

        local_max = max(length_values) if length_values else 0
        if local_max > max_length:
            max_length = local_max

    apply_log_ticks(ax, max_length)
    ax.xaxis.set_major_formatter(format_big_number)

    ax.set_title("WPM PB Per Quote Length")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("WPM")

    apply_theme(ax, theme=theme, legend_loc=1, force_legend=True, themed_line=themed_line)

    file_name = generate_file_name("endurance")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
