import numpy as np

from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    metric: dict,
    solo_values: list[float],
    multi_values: list[float],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    solo_values = np.array(solo_values)
    multi_values = np.array(multi_values)
    values = np.concatenate([solo_values, multi_values])

    ax.set_title(f"{metric["title"]} Histogram - {username}")
    ax.set_ylabel("Occurrences")
    ax.set_xlabel(metric["x_label"])

    match metric["name"]:
        case "pp":
            bins = np.arange(min(values), max(values), 10)
        case "wpm":
            bins = np.arange(min(values), max(values), 5)
        case "accuracy":
            min_display_acc = 85
            bins = np.floor(np.arange(np.floor(max(min(values), min_display_acc)), 101.1, 1))
        case "errorReactionTime" | "errorRecoveryTime":
            values = [v for v in values if 0 < v < 600]
            bins = np.arange(min(values), max(values), 10)

    if color in plt.colormaps():
        color = "#00B5E2"

    heights = []
    if len(solo_values) > 0:
        n, _, _ = ax.hist(solo_values, bins=bins, color=color, label="Solo", alpha=0.5)
        heights.extend(n)
    if len(multi_values) > 0:
        n, _, _ = ax.hist(multi_values, bins=bins, color=invert_color(color), label="Multi", alpha=0.5)
        heights.extend(n)

    # Capping Y limit
    if metric["name"] == "accuracy":
        bin_centers = (bins[:-1] + bins[1:]) / 2
        heights_below_100 = [h for h, c in zip(heights, bin_centers) if c < 100]
        if heights_below_100:
            ax.set_ylim(0, max(heights_below_100) * 1.1)

    ax.legend()
    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def invert_color(color: str):
    return f"#{0xFFFFFF ^ int(color.lstrip("#"), 16):06x}"
