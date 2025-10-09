import numpy as np

from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    metric: dict,
    solo_stats: list[float],
    multi_stats: list[float],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    solo_stats = np.array(solo_stats)
    multi_stats = np.array(multi_stats)
    quote_bests_stats = np.concatenate([solo_stats, multi_stats])

    ax.set_title(f"{metric["title"]} Histogram - {username}")
    ax.set_ylabel("Occurrences")
    ax.set_xlabel(metric["x_label"])

    match metric["name"]:
        case "pp":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 10)
        case "wpm":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 5)
        case "accuracy":
            min_display_acc = 85
            bins = np.floor(np.arange(np.floor(max(min(quote_bests_stats), min_display_acc)), 101.1, 1))
        case "errorReactionTime" | "errorRecoveryTime":
            quote_bests_stats = [v for v in quote_bests_stats if 0 < v < 600]
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 10)

    if color in plt.colormaps():
        color = "#00B5E2"

    ax.hist(solo_stats, bins=bins, color=color, label="Solo", alpha=0.5)
    ax.hist(multi_stats, bins=bins, color=invert_color(color), label="Multi", alpha=0.5)

    ax.legend()
    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def invert_color(color: str):
    return f"#{0xFFFFFF ^ int(color.lstrip("#"), 16):06x}"
