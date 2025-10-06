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
        ax.hist(quote_bests_stats, bins=bins, alpha=0)
    else:
        ax.hist(quote_bests_stats, bins=bins, color=color)

    counts, groups = np.histogram(quote_bests_stats, bins=bins)

    if color in plt.colormaps():
        apply_colormap(ax, counts, groups, theme)

    ax.set_title(f"{metric} histogram - {username}")
    ax.set_xlabel(f"{metric}")
    ax.set_ylabel("Occurences")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

def apply_colormap(ax, counts, groups, theme):
    """Apply colormap to vertical histogram bars with masked gradient background."""
    cmap = plt.get_cmap(theme["line"])
    
    ax.bar(groups[:-1], counts, width=np.diff(groups), align="edge", alpha=0)

    y = np.linspace(0, max(counts), 100)
    x = np.linspace(groups[0], groups[-1], 100)
    _, Y = np.meshgrid(x, y)
    ax.imshow(Y, cmap=cmap, extent=[groups[0], groups[-1], 0, max(counts)], origin='lower', aspect='auto')

    graph_background = theme["graph_background"]
    mask_height = max(counts) - counts
    ax.bar(groups[:-1], mask_height, width=np.diff(groups), bottom=counts,
           align="edge", color=graph_background, edgecolor='none')
