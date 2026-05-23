from dataclasses import dataclass
from typing import List

import numpy as np

from graphs.core import plt, apply_theme, generate_file_name, filter_palette, apply_log_ticks
from utils.strings import format_big_number

BUCKETS = 60


@dataclass
class UserLengthData:
    username: str
    values: List[float]
    lengths: List[int]


def bucket_by_log(lengths: List[int], values: List[float]) -> tuple[List[float], List[float]]:
    """Bin (length, value) pairs into log-spaced buckets, keeping the max value per bucket."""
    log_min = np.log10(min(lengths))
    log_max = np.log10(max(lengths))
    edges = np.logspace(log_min, log_max, BUCKETS + 1)

    bucketed_lengths, bucketed_values = [], []
    for i in range(len(edges) - 1):
        pairs = [(l, v) for l, v in zip(lengths, values) if edges[i] <= l < edges[i + 1]]
        if pairs:
            ls, vs = zip(*pairs)
            bucketed_lengths.append(float(np.mean(ls)))
            bucketed_values.append(max(vs))

    return bucketed_lengths, bucketed_values


def render(
    first_username: str,
    data: List[UserLengthData],
    metric: str,
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    themed_line = 0
    max_length = 0
    data_count = len(data)

    for line_index, user_data in enumerate(data):
        if user_data.username == first_username:
            themed_line = line_index

        lengths, values = bucket_by_log(user_data.lengths, user_data.values)
        ax.plot(lengths, values, label=user_data.username, zorder=data_count - line_index)

        local_max = max(lengths) if lengths else 0
        if local_max > max_length:
            max_length = local_max

    apply_log_ticks(ax, max_length)
    ax.xaxis.set_major_formatter(format_big_number)

    y_label = "pp" if metric == "pp" else "WPM"
    ax.set_title(f"{y_label} PB Per Quote Length")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel(y_label)

    apply_theme(ax, theme=theme, legend_loc=1, force_legend=True, themed_line=themed_line)

    file_name = generate_file_name("lengthgraph")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
