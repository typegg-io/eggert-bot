import numpy as np
from matplotlib import patches

from graphs.core import plt, apply_theme, generate_file_name


def render(
    segments: list[dict],
    title: str,
    x_label: str,
    theme: dict,
):
    fig, ax = plt.subplots()

    x = list(range(1, len(segments) + 1))
    y = [0 if s["wpm"] == float("inf") else s["wpm"] for s in segments]
    raw_y = [0 if s["raw_wpm"] == float("inf") else s["raw_wpm"] for s in segments]

    all_values = y + [v for v in raw_y if v > 0]
    y_limit = calculate_y_limit(all_values)

    width = 1 if len(x) > 200 else 0.8
    if theme["line"] in plt.colormaps():
        apply_colormap(ax, theme, x, y, raw_y, width, y_limit)
    else:
        ax.bar(x, y, color=theme["line"], width=width)
        ax.bar(x, raw_y, color=theme["raw_speed"], zorder=0, width=width)
        ax.set_ylim(0, y_limit * 1.05)

    ax.set_ylabel("WPM")
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.grid()
    apply_theme(ax, theme)

    file = generate_file_name("segments")
    plt.savefig(file)
    plt.close(fig)

    return file


def apply_colormap(ax, theme, x_values, wpm_values, raw_values, width, y_limit):
    """Apply a colormap gradient to bars, masking areas outside bars with background."""
    cmap = plt.get_cmap(theme["line"])
    background = theme["graph_background"]
    ylim = (0, y_limit * 1.05)

    # Create invisible bars to establish dimensions
    bars = ax.bar(x_values, wpm_values, alpha=0, width=width)
    bar_width = bars[0].get_width()

    # Draw raw speed bars if they extend above wpm bars
    if raw_values:
        for i, bar in enumerate(bars):
            if raw_values[i] > wpm_values[i]:
                ax.add_patch(patches.Rectangle(
                    (bar.get_x(), bar.get_height()),
                    bar_width,
                    raw_values[i] - bar.get_height(),
                    color=theme["raw_speed"],
                ))

    # Draw gradient background
    ax.set_ylim(ylim)
    gradient = np.linspace(0, 10, 100).reshape(-1, 1)
    extent = [ax.get_xlim()[0], ax.get_xlim()[1], 0, max(wpm_values)]
    ax.imshow(gradient, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_ylim(ylim)

    # Mask above each bar
    display_values = raw_values if raw_values else wpm_values
    for i, bar in enumerate(bars):
        height = max(wpm_values[i], display_values[i]) if raw_values else bar.get_height()
        ax.add_patch(patches.Rectangle(
            (bar.get_x(), height),
            bar_width,
            ylim[1] - height,
            color=background,
        ))

    # Mask gaps between bars (only when not edge-to-edge)
    if width < 1:
        for i in range(len(x_values) - 1):
            left = x_values[i] + bar_width / 2
            right = x_values[i + 1] - bar_width / 2
            ax.add_patch(patches.Rectangle(
                (left, 0), right - left, ylim[1], color=background
            ))

    # Mask left and right padding
    xlim = ax.get_xlim()
    ax.add_patch(patches.Rectangle(
        (xlim[0], 0),
        x_values[0] - bar_width / 2 - xlim[0],
        ylim[1],
        color=background,
    ))
    ax.add_patch(patches.Rectangle(
        (x_values[-1] + bar_width / 2, 0),
        xlim[1] - (x_values[-1] + bar_width / 2),
        ylim[1],
        color=background,
    ))


def calculate_y_limit(values: list[float], percentile: int = 99) -> float:
    """Calculate y-axis limit, capping outliers using percentile."""
    cap = np.percentile(values, percentile)
    actual_max = max(values)
    return actual_max if actual_max < cap else cap
