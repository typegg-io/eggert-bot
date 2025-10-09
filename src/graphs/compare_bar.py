import math

import numpy as np
from matplotlib import patches
from matplotlib.ticker import FixedLocator

from graphs.core import plt, apply_theme, generate_file_name


def render(
    username1: str,
    gains1: dict[int, int],
    username2: str,
    gains2: dict[int, int],
    defaults: dict[int, int],
    theme: dict,
):
    difficulty_range = sorted(list(gains1.keys() | gains2.keys()))
    min_difficulty = 1
    max_difficulty = math.ceil(max(max(difficulty_range), 7) + 0.5)
    difficulties = np.arange(min_difficulty, max_difficulty, 0.5)

    values1 = [gains1.get(bucket, 0) for bucket in difficulties]
    values2 = [gains2.get(bucket, 0) for bucket in difficulties]
    values3 = [defaults.get(bucket, 0) for bucket in difficulties]

    x_limit = max(values1 + values2) * 1.1

    fig, ax = plt.subplots()

    is_colormap = theme["line"] in plt.colormaps()
    if is_colormap:
        color, alpha1, alpha2 = "white", 0, 0
    else:
        color, alpha1, alpha2 = theme["line"], 1, 0.15

    y_pos = np.arange(len(difficulties))
    ax.barh(y_pos, [-v for v in values1], height=1, alpha=alpha1, color=color)
    ax.barh(y_pos, values2, height=1, alpha=alpha1, color=color)
    ax.barh(y_pos, values3, height=1, alpha=alpha2, color=color)

    ax.set_xlim(-x_limit, x_limit)
    xticks = ax.get_xticks()
    ax.xaxis.set_major_locator(FixedLocator(xticks))
    ax.set_xticklabels([abs(int(x)) for x in xticks])

    if is_colormap:
        apply_colormap(ax, gains1, gains2, defaults, difficulties, theme)

    edges = np.arange(len(difficulties) + 1) - 0.5
    labels = np.arange(min(difficulties), max(difficulties) + 1, 0.5)
    ax.set_yticks(edges)
    ax.set_yticklabels([
        str(int(y)) if y.is_integer() else ""
        for y in labels
    ])

    apply_theme(ax, theme)
    ax.axvline(x=0, color=theme["axis"], linewidth=0.8)

    ax.set_xlabel("Number of Quotes")
    ax.set_ylabel("Difficulty")
    fig.suptitle("Quote Bests Comparison", color=theme["text"], fontsize=12, y=0.98)
    ax.text(
        0.25, 1.02, username1, transform=ax.transAxes,
        ha='center', va='bottom', fontsize=12, color=theme["text"]
    )
    ax.text(
        0.75, 1.02, username2, transform=ax.transAxes,
        ha='center', va='bottom', fontsize=12, color=theme["text"]
    )

    file_name = generate_file_name("compare")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_colormap(ax, gains1, gains2, defaults, difficulties, theme):
    """Apply colormap to a bar graph by creating a masked gradient background."""
    cmap = plt.get_cmap(theme["line"])

    x_limit = ax.get_xlim()[0]
    extent_left = [-x_limit, 0, -0.5, len(difficulties) - 0.5]
    extent_right = [0, x_limit, -0.5, len(difficulties) - 0.5]

    grad_left = np.linspace(1, 0, 256).reshape(1, -1)
    grad_right = np.linspace(0, 1, 256).reshape(1, -1)

    original_ylim = ax.get_ylim()
    original_xlim = ax.get_xlim()

    ax.imshow(grad_left, aspect='auto', cmap=cmap, extent=extent_left)
    ax.imshow(grad_right, aspect='auto', cmap=cmap, extent=extent_right)

    ax.set_ylim(original_ylim)
    ax.set_xlim(original_xlim)

    for i, bucket in enumerate(difficulties):
        # Right Side
        gain2 = gains2[bucket]
        default = defaults[bucket]
        if default < 0:
            default = 0
        min_value = min(gain2, default)
        max_value = max(gain2, default)
        max_value = min(max_value, -x_limit)

        rect = patches.Rectangle(
            xy=(max_value, i - 0.5),
            width=-x_limit - max_value,
            height=1,
            alpha=1,
            color=theme["graph_background"],
            linewidth=0,
        )
        ax.add_patch(rect)

        if gain2 < default:
            rect = patches.Rectangle(
                xy=(min_value, i - 0.5),
                width=max_value - min_value,
                height=1,
                alpha=0.85,
                color=theme["graph_background"],
                linewidth=0,
            )
            ax.add_patch(rect)

        # Left Side
        gain1 = gains1[bucket]
        gain1 = -gain1
        default = defaults[bucket]
        if default > 0:
            default = 0
        min_value = max(gain1, default)
        max_value = min(gain1, default)
        max_value = max(max_value, x_limit)

        rect = patches.Rectangle(
            xy=(x_limit, i - 0.5),
            width=abs(x_limit - max_value),
            height=1,
            alpha=1,
            color=theme["graph_background"],
            linewidth=0,
        )
        ax.add_patch(rect)

        if gain1 > default:
            rect = patches.Rectangle(
                xy=(min_value, i - 0.5),
                width=max_value - min_value,
                height=1,
                alpha=0.85,
                color=theme["graph_background"],
                linewidth=0,
            )
            ax.add_patch(rect)
