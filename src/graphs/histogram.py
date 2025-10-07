from graphs.core import plt, apply_theme, generate_file_name
import numpy as np
from utils.errors import InvalidArgument


def render(
    username: str,
    metric: str,
    multi_stats: list[float],
    solo_stats: list[float],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    solo_stats = np.array(solo_stats)
    multi_stats = np.array(multi_stats)
    quote_bests_stats = np.concatenate([solo_stats, multi_stats])

    ax.set_title(f"{metric.capitalize()} Histogram - {username}")
    ax.set_ylabel("Occurences")

    match metric:
        case "pp":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 10)
            ax.set_xlabel(f"Typing Performance (in pp)")
        case "wpm":
            bins = np.arange(min(quote_bests_stats), max(quote_bests_stats), 5)
            ax.set_xlabel(f"Typing Speed (in wpm)")
        case "accuracy":
            min_display_acc = 0.85
            bins = np.floor(np.arange(np.floor(max(min(quote_bests_stats), min_display_acc) * 100) / 100, 1.011, 0.01) * 100)

            solo_stats *= 100
            multi_stats *= 100
            ax.set_xlabel(f"Accuracy (in %)")
        case _:
            raise InvalidArgument(f"invalid metric: {metric}")

    if color in plt.colormaps():
        color = "#00B5E2"

    ax.hist(solo_stats, bins=bins, color=color, label="solo", alpha=0.5)
    ax.hist(multi_stats, bins=bins, color=invertColor(color), label="multi", alpha=0.5)

    ax.legend()
    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

def invertColor(color: str):
    return f"#{0xFFFFFF ^ int(color.lstrip('#'), 16):06x}"

