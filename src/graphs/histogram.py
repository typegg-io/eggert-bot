from graphs.core import plt, apply_theme, generate_file_name
import numpy as np
from utils.errors import InvalidArgument


def render(
    username: str,
    metric: str,
    quote_bests_stats: list[float],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    quote_bests_stats = np.array(quote_bests_stats)

    match metric:
        case "pp":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 10)
        case "wpm":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 5)
        case "accuracy":
            min_display_acc = 0.85
            bins = np.floor(np.arange(np.floor(max(min(quote_bests_stats), min_display_acc) * 100) / 100, 1.011, 0.01) * 100)
            quote_bests_stats *= 100
        case _:
            raise InvalidArgument("invalid metric")



    if color in plt.colormaps():
        ax.hist(quote_bests_stats, bins=bins, cmap=color)
    else:
        ax.hist(quote_bests_stats, bins=bins, color=color)

    ax.set_title(f"{metric} histogram - {username}")
    ax.set_xlabel(f"{metric}")
    ax.set_ylabel("Occurences")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

def apply_colormap(ax, counts, groups, extent, theme):
    """Apply colormap to histogram bars by creating a masked gradient background."""
    cmap = plt.get_cmap(theme["line"])

    mask = np.zeros((len(groups), 2))
    mask[:, 0] = np.concatenate([groups[:-1], [groups[-1]]])
    mask[:-1, 1] = counts

    ax.barh(groups[:-1], counts, height=np.diff(groups), align="edge", alpha=0)
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
