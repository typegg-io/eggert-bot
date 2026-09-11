"""The personal best progression graph, over races and over time."""

import numpy as np
from matplotlib.colors import hex2color
from matplotlib.ticker import FuncFormatter

from graphs.core import apply_date_ticks, apply_theme, generate_file_name, plt
from utils.schemas import Theme
from utils.strings import format_big_number


def render(
    x: list[float],
    values: list[float],
    best_indices: list[int],
    milestone_indices: list[int],
    metric: str,
    theme: Theme,
    over_time: bool,
) -> str:
    """Render every race behind a step line of the running best and return the file name."""
    fig, ax = plt.subplots()
    x = np.asarray(x, dtype=float)
    values = np.asarray(values, dtype=float)

    step_x, step_y = [], []
    for k, i in enumerate(best_indices):
        end = best_indices[k + 1] if k + 1 < len(best_indices) else len(values) - 1
        step_x += [x[i], x[end]]
        step_y += [values[i], values[i]]
    ax.plot(step_x, step_y, label="_")

    bg_color = hex2color(theme["graph_background"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"

    downsample_factor = max(len(values) // 100000, 1)
    ax.scatter(
        x[::downsample_factor], values[::downsample_factor],
        alpha=0.1, s=25, color=point_color, edgecolors="none",
    )
    ax.scatter(x[best_indices], values[best_indices], color=point_color, marker=".", zorder=10, s=20)
    ax.scatter(x[milestone_indices], values[milestone_indices], color="#53D76A", marker=".", zorder=12, s=60)
    ax.scatter(x[best_indices[-1]], values[best_indices[-1]], color="#FFB600", marker="*", zorder=15, s=80)

    if over_time:
        apply_date_ticks(ax, x)
        ax.set_xlabel("Date")
    else:
        ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
        ax.set_xlabel("Race Number")

    bottom = min(np.percentile(values, 1), values[best_indices[0]])
    top = values[best_indices[-1]]
    margin = max((top - bottom) * 0.05, 1)
    ax.set_ylim(bottom=bottom - margin, top=top + margin)

    ax.set_ylabel(metric)
    ax.set_title(f"{metric} Personal Best Progression")
    ax.grid()

    apply_theme(ax, theme)

    file_name = generate_file_name("personal_best")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
