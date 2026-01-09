from dataclasses import dataclass, astuple
from typing import List
from numpy import append
from graphs.core import plt, apply_theme, generate_file_name, filter_palette
from matplotlib.ticker import MaxNLocator
from utils.prettify_xticks import prettyfyLogLengthXticks


@dataclass
class UserEnduranceData:
    username: str
    wpm_values: List[float]
    length_values: List[int]


def render(
    first_username: str,
    data: List[UserEnduranceData],
    log_base: int,
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    max_length = 0
    themed_line = 0

    for i, (username, wpm_values, length_values) in enumerate(map(astuple, data)):
        if username == first_username:
            themed_line = i

        ax.step(length_values, wpm_values, where="pre", label=username)

        local_max_length = max(length_values)

        if local_max_length > max_length:
            max_length = local_max_length

    ax.set_title("WPM PB Per Quote Length")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("WPM")

    ax.xaxis.set_major_locator(MaxNLocator(nbins=10))
    xticks = ax.get_xticks()
    xticks = append(xticks[:-1], max_length)  # Make the max xtick equal to the max length
    xticks = prettyfyLogLengthXticks(xticks, log_base, min_overlapping_scale=0.068)

    ax.set_xticks(xticks)

    ax.set_xticklabels([f"{xtick:.0f}" for xtick in log_base ** ax.get_xticks()])
    apply_theme(ax, theme=theme, legend_loc=1, force_legend=True, themed_line=themed_line)

    file_name = generate_file_name("endurance")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

