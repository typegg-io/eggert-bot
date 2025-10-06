import numpy as np

from graphs.core import plt, apply_theme, generate_file_name


def render(
    username1: str,
    gains1: list[float],
    username2: str,
    gains2: list[float],
    metric: str,
    theme: dict,
):
    fig, (ax1, ax2) = plt.subplots(1, 2)

    color = theme["line"]
    if color in plt.colormaps():
        ax1.hist(gains1, bins="auto", orientation="horizontal", alpha=0)
        ax2.hist(gains2, bins="auto", orientation="horizontal", alpha=0)
    else:
        ax1.hist(gains1, bins="auto", orientation="horizontal", color=color)
        ax2.hist(gains2, bins="auto", orientation="horizontal", color=color)

    if metric == "wpm":
        metric = metric.upper()
    ax1.set_ylabel(f"{metric} Difference")
    ax2.yaxis.tick_right()

    max_xlim = max(ax1.get_xlim()[1], ax2.get_xlim()[1])
    ax2.set_xlim(0, max_xlim)
    ax1.set_xlim(ax2.get_xlim()[::-1])

    min_ylim = min(ax1.get_ylim()[0], ax2.get_ylim()[0])
    max_ylim = max(ax1.get_ylim()[1], ax2.get_ylim()[1])
    ax1.set_ylim(min_ylim, max_ylim)
    ax2.set_ylim(min_ylim, max_ylim)

    if color in plt.colormaps():
        counts1, groups1 = np.histogram(gains1, bins="auto")
        counts2, groups2 = np.histogram(gains2, bins="auto")
        apply_colormap(ax1, counts1, groups1, [0, max(counts1), min_ylim, max_ylim], theme)
        apply_colormap(ax2, counts2, groups2, [0, max(counts2), min_ylim, max_ylim], theme)

    ax1.grid()
    ax1.set_title(username1)

    ax2.grid()
    ax2.set_title(username2)

    apply_theme(ax1, theme)
    apply_theme(ax2, theme)

    plt.subplots_adjust(wspace=0, hspace=0)

    fig.suptitle(f"Quote Bests Comparison", color=theme["text"])
    fig.text(0.5, 0.025, "Number of Quotes", ha="center", color=theme["text"])

    file_name = generate_file_name("compare")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_colormap(ax, counts, groups, extent, theme):
    """Apply colormap to histogram bars by creating a masked gradient background."""
    cmap = plt.get_cmap(theme["line"])

    mask = np.zeros((len(groups), 2))
    mask[:, 0] = np.concatenate([groups[:-1], [groups[-1]]])
    mask[:-1, 1] = counts

    ax.barh(groups[:-1], counts)
    original_xlim = ax.get_xlim()

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(X, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_xlim(original_xlim)

    graph_background = theme["graph_background"]
    ax.fill_betweenx(mask[:, 0], mask[:, 1], extent[1], color=graph_background, step='post')
    ax.fill_betweenx([extent[2], groups[0]], [0, 0], [extent[1], extent[1]], color=graph_background)
    ax.fill_betweenx([groups[-1], extent[3]], [0, 0], [extent[1], extent[1]], color=graph_background)
