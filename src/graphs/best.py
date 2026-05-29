from typing import Dict, List

import numpy as np
from matplotlib.colors import hex2color

from graphs.core import plt, apply_theme, generate_file_name, filter_palette


def render(
    username: str,
    profiles: List[Dict],
    n: int,
    metric: str,
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])
    themed_line = 0
    profile_count = len(profiles)

    for i, profile in enumerate(profiles):
        values = profile["values"]

        if profile["username"] == username:
            themed_line = i

        ax.plot(range(1, len(values) + 1), values, label=profile["username"], zorder=profile_count - i)

    ax.set_title(f"Top {n:,} {metric} Quotes")
    ax.set_xlabel("Quote Rank")
    ax.set_ylabel(metric)

    apply_theme(
        ax,
        theme=theme,
        legend_loc=1,
        force_legend=profile_count > 1,
        themed_line=themed_line
    )

    if profile_count == 1:
        difficulties = profiles[0]["difficulties"]
        bg_color = hex2color(theme["graph_background"])
        point_color = "white" if np.mean(bg_color) < 0.5 else "black"

        ax2 = ax.twinx()
        ax2.scatter(
            np.arange(1, len(difficulties) + 1), difficulties,
            label="_", alpha=0.1, s=25, color=point_color, edgecolors="none"
        )

        ax.set_zorder(ax2.get_zorder() + 1)
        ax.patch.set_visible(False)

        ax2.set_ylabel("Difficulty")
        apply_theme(ax2, theme | {"line": "#808080", "grid_opacity": 0})

    file_name = generate_file_name("top250")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
