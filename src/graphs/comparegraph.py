import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from graphs.core import apply_cmap, color_graph

def render(color, comparison_data, output_file):
    username1 = comparison_data["firstUser"]["username"]
    username2 = comparison_data["secondUser"]["username"]
    metric = comparison_data["metric"].upper()

    first_user_buckets = comparison_data["histogram"]["firstUser"]
    second_user_buckets = comparison_data["histogram"]["secondUser"]

    diffs1 = [bucket["difference"] for bucket in first_user_buckets]
    counts1 = [bucket["count"] for bucket in first_user_buckets]

    diffs2 = [bucket["difference"] for bucket in second_user_buckets]
    counts2 = [bucket["count"] for bucket in second_user_buckets]

    fig, (ax1, ax2) = plt.subplots(1, 2)

    user = {
        "colors": {
            "line": color,
            "text": "#ffffff",
            "axis": "#777777",
            "grid": "#555555",
            "background": "#36393f",
            "graphbackground": "#36393f",
            "raw": "#AAAAAA"
        },
        "id": 0
    }

    if color in plt.colormaps():
        if diffs1 and counts1:
            ax1.barh(diffs1, counts1, height=4.5, align='center', alpha=0)
        if diffs2 and counts2:
            ax2.barh(diffs2, counts2, height=4.5, align='center', alpha=0)
    else:
        if diffs1 and counts1:
            ax1.barh(diffs1, counts1, height=4.5, align='center', color=color)
        if diffs2 and counts2:
            ax2.barh(diffs2, counts2, height=4.5, align='center', color=color)

    ax1.set_ylabel(f"{metric} Difference")
    ax2.yaxis.tick_right()

    max_count = max(max(counts1) if counts1 else 0, max(counts2) if counts2 else 0)
    if max_count == 0:
        max_count = 1

    ax2.set_xlim(0, max_count * 1.1)
    ax1.set_xlim(ax2.get_xlim()[::-1])

    # y-axis limits
    all_diffs = diffs1 + diffs2
    if all_diffs:
        min_diff = min(all_diffs)
        max_diff = max(all_diffs)
        padding = 10.0

        min_ylim = max(0, min_diff - padding)
        max_ylim = max_diff + padding
    else:
        min_ylim, max_ylim = 0, 25

    ax1.set_ylim(min_ylim, max_ylim)
    ax2.set_ylim(min_ylim, max_ylim)

    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.7)

    if color in plt.colormaps():
        groups1 = np.array(diffs1)
        groups2 = np.array(diffs2)

        apply_cmap(ax1, user, counts1, groups1, [0, max_count * 1.1, min_ylim, max_ylim])
        apply_cmap(ax2, user, counts2, groups2, [0, max_count * 1.1, min_ylim, max_ylim])

    ax1.grid()
    ax1.set_title(username1)

    ax2.grid()
    ax2.set_title(username2)

    color_graph(ax1, user)
    color_graph(ax2, user)

    plt.subplots_adjust(wspace=0, hspace=0)

    fig.suptitle(f"Text Bests Comparison ({metric})", color=user["colors"]["text"])
    fig.text(0.5, 0.025, "Number of Texts", ha="center", color=user["colors"]["text"])

    plt.savefig(output_file, facecolor=user["colors"]["background"])
    plt.close(fig)

    return output_file
