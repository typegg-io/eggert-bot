"""The improvement over time and over races graphs."""

import numpy as np
from matplotlib.colors import hex2color
from matplotlib.ticker import FuncFormatter, MaxNLocator
from numpy.lib.stride_tricks import sliding_window_view

from graphs.core import apply_date_ticks, apply_theme, generate_file_name, interpolate_segments, plt
from utils.dates import get_timestamp_list
from utils.schemas import Theme
from utils.strings import format_big_number


def moving_line(values: np.ndarray, window_size: int, placements: bool) -> np.ndarray:
    """Return the moving average, or the moving median for placements."""
    if placements:
        return np.median(sliding_window_view(values, window_size), axis=1)
    return np.convolve(values, np.ones(window_size) / window_size, mode="valid")


def fit_placements(ax, values: np.ndarray, line: np.ndarray) -> None:
    """Show placements on a whole number axis with first place at the top."""
    low = min(values.min(), line.min())
    high = max(np.percentile(values, 95), line.max(), low + 1)
    ax.set_ylim(high + 0.5, low - 0.5)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))


def render_over_time(
    values: list[float],
    metric: str,
    theme: Theme,
    dates: list[str],
    window_size: int,
    dnf_indices: list[int] = None,
    ceiling: float | None = None,
    unit: str = "Races",
    placements: bool = False,
) -> str:
    """Render a metric over dates and return the file name."""
    fig, ax = plt.subplots()
    values = np.asarray(values)

    downsample_factor = max(len(values) // 100000, 1)
    downsampled_indices = np.arange(0, len(values), downsample_factor)
    downsampled_values = values[downsampled_indices]

    if len(values) > 10000:
        downsample_factor *= 10

    moving_average = moving_line(values, window_size, placements)[0::downsample_factor]
    x_points = np.arange(window_size - 1, len(values))[0::downsample_factor]

    timestamps = np.asarray(get_timestamp_list(dates))
    downsampled_indices = [timestamps[d] for d in downsampled_indices]
    x_points = [timestamps[r] for r in x_points]
    apply_date_ticks(ax, timestamps)

    bg_color = hex2color(theme["graph_background"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"

    ax.scatter(downsampled_indices, downsampled_values, alpha=0.1, s=25, color=point_color, edgecolors="none")

    segment_count = 50 // (len(moving_average) - 1) if len(moving_average) > 1 else 1
    if segment_count > 1:
        x_segments, y_segments = interpolate_segments(x_points, moving_average)
        ax.plot(x_segments, y_segments, label="_")
    else:
        ax.plot(x_points, moving_average, label="_")

    if dnf_indices:
        dnf_indices = np.asarray(dnf_indices)
        dnf_mask = dnf_indices[window_size - 1:][0::downsample_factor]
        dnf_x = np.asarray(x_points)[dnf_mask]
        dnf_y = moving_average[dnf_mask]
        ax.scatter(dnf_x, dnf_y, color=theme["crosses"], s=1, zorder=999, label="_")

    ax.set_xlabel("Date")
    ax.set_ylabel(metric)
    title = f"{metric} Improvement"

    if window_size > 1:
        title += f"\nMoving {'Median' if placements else 'Average'} of {window_size} {unit}"

    low = np.percentile(downsampled_values, 1)
    if placements:
        fit_placements(ax, values, moving_average)
    elif ceiling is None:
        ax.set_ylim(top=np.percentile(downsampled_values, 95) * 1.05, bottom=low * 0.95)
    else:
        # Values crowd the ceiling, so scaling the low percentile would lift the axis past every point.
        margin = max((ceiling - low) * 0.05, 0.5)
        ax.set_ylim(top=ceiling + margin, bottom=low - margin)

    ax.set_title(title)
    ax.grid()
    ax.set_title(title)

    apply_theme(ax, theme)

    file_name = generate_file_name("improvement")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def render_over_races(
    values: list[float],
    secondary: list[float] | None,
    metric: str,
    theme: Theme,
    window_size: int,
    dnf_indices: list[int] = None,
    unit: str = "Races",
    placements: bool = False,
    secondary_label: str = "Difficulty",
    invert_secondary: bool = True,
) -> str:
    """Render a metric over race numbers, with a secondary line when given, and return the file name."""
    fig, ax = plt.subplots()
    ax2 = ax.twinx() if secondary is not None else None

    values = np.asarray(values)
    kernel = np.ones(window_size) / window_size

    x_points = np.arange(window_size - 1, len(values))
    moving_average = moving_line(values, window_size, placements)

    x_points = [r + 1 for r in x_points]
    ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    segment_count = 50 // (len(moving_average) - 1) if len(moving_average) > 1 else 1
    if segment_count > 1:
        x_average, y_average = interpolate_segments(x_points, moving_average)
        ax.plot(x_average, y_average, label="_")
    else:
        ax.plot(x_points, moving_average, label="_")

    if ax2:
        secondary_average = np.convolve(np.asarray(secondary), kernel, mode="valid")
        if segment_count > 1:
            x_secondary, y_secondary = interpolate_segments(x_points, secondary_average)
            ax2.plot(x_secondary, y_secondary, label="_", alpha=0.5)
        else:
            ax2.plot(x_points, secondary_average, label="_", alpha=0.5)

    if dnf_indices:
        dnf_indices = np.asarray(dnf_indices)
        dnf_mask = dnf_indices[window_size - 1:]
        dnf_x = np.asarray(x_points)[dnf_mask]
        dnf_y = moving_average[dnf_mask]
        ax.scatter(dnf_x, dnf_y, color=theme["crosses"], s=1, zorder=999, label="_")

    ax.set_ylabel(metric)
    ax.set_xlabel(unit)
    if placements:
        fit_placements(ax, values, moving_average)
    if ax2:
        if invert_secondary:
            ax2.invert_yaxis()
        ax2.set_ylabel(secondary_label)
    title = f"{metric} Improvement"

    if window_size > 1:
        title += f"\nMoving {'Median' if placements else 'Average'} of {window_size} {unit}"

    ax.set_title(title)
    ax.grid()
    ax.set_title(title)

    apply_theme(ax, theme)
    if ax2:
        apply_theme(ax2, theme | {"line": "#808080", "grid_opacity": 0})

    file_name = generate_file_name("improvement")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def render_text(
    values: list[float],
    metric: str,
    quote_id: str,
    theme: Theme,
) -> str:
    """Render a metric over one quote's races and return the file name."""
    fig, ax = plt.subplots()
    values = np.array(values)

    downsample_factor = max(len(values) // 100000, 1)
    downsampled_indices = np.arange(0, len(values), downsample_factor)
    downsampled_values = values[downsampled_indices]
    window_size = min(max(len(values) // 15, 1), 50)

    if len(values) > 10000:
        downsample_factor *= 10

    moving_values = np.convolve(values, np.ones(window_size) / window_size, mode="valid")[0::downsample_factor]
    x_points = np.arange(window_size - 1, len(values))[0::downsample_factor]

    downsampled_indices = [d + 1 for d in downsampled_indices]
    x_points = [r + 1 for r in x_points]
    ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))

    bg_color = hex2color(theme["graph_background"])
    point_color = "white" if np.mean(bg_color) < 0.5 else "black"

    ax.scatter(downsampled_indices, downsampled_values, alpha=0.1, s=25, color=point_color, edgecolors="none")

    segment_count = 50 // (len(moving_values) - 1) if len(moving_values) > 1 else 1
    if len(x_points) >= window_size:
        if segment_count > 1:
            x_segments, y_segments = interpolate_segments(x_points, moving_values)
            ax.plot(x_segments, y_segments, label="_")
        else:
            ax.plot(x_points, moving_values, label="_")

    personal_bests = []
    current_best = float("-inf")
    for i, value in enumerate(values):
        if value > current_best:
            personal_bests.append((i + 1, value))
            current_best = value

    x_best, y_best = zip(*personal_bests)
    ax.scatter(x_best, y_best, color="#53D76A", marker=".", zorder=10, s=35)
    ax.scatter(x_best[-1], y_best[-1], color="#FFB600", marker="*", zorder=15, s=35)

    metric = ["WPM", "pp"][metric == "pp"]
    ax.set_xlabel("Races")
    ax.set_ylabel(metric)
    title = f"{metric} Improvement - Quote {quote_id}"
    if window_size > 1:
        title += f"\nMoving Average of {window_size} Races"
    ax.set_title(title)
    ax.grid()
    ax.set_title(title)

    apply_theme(ax, theme)

    file_name = generate_file_name("text_improvement")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
