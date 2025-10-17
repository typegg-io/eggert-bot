import numpy as np
from matplotlib.colors import hex2color
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, apply_theme, interpolate_segments, apply_date_ticks, generate_file_name
from utils.dates import get_timestamp_list
from utils.strings import format_big_number


def render(
    values: list[float],
    metric: str,
    theme: dict,
    dates: list[str] = None,
    window_size: int = None,
):
    fig, ax = plt.subplots()
    values = np.array(values)
    best_index, best = max(enumerate(values), key=lambda x: x[1])

    downsample_factor = max(len(values) // 100000, 1)
    downsampled_indices = np.arange(0, len(values), downsample_factor)
    downsampled_values = values[downsampled_indices]
    if not window_size:
        window_size = min(max(len(values) // 15, 1), 500)

    if len(values) > 10000:
        downsample_factor *= 10

    moving_values = np.convolve(values, np.ones(window_size) / window_size, mode="valid")[0::downsample_factor]
    x_points = np.arange(window_size - 1, len(values))[0::downsample_factor]

    if dates:
        timestamps = np.array(get_timestamp_list(dates))
        downsampled_indices = [timestamps[d] for d in downsampled_indices]
        x_points = [timestamps[r] for r in x_points]
        ax.scatter(timestamps[best_index], best, color="#53D76A", marker=".", zorder=10)
        apply_date_ticks(ax, timestamps)

    else:
        downsampled_indices = [d + 1 for d in downsampled_indices]
        x_points = [r + 1 for r in x_points]
        ax.scatter(best_index + 1, best, color="#53D76A", marker=".", zorder=10)
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

    if dates:
        ax.set_xlabel(f"Date")
    else:
        ax.set_xlabel(f"Races")
    ax.set_ylabel(metric)
    title = f"{metric} Improvement"
    if window_size > 1:
        title += f"\nMoving Average of {window_size} Races"
    ax.set_title(title)
    ax.grid()
    ax.set_title(title)

    apply_theme(ax, theme)

    file_name = generate_file_name("improvement")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def render_text(
    values: list[float],
    quote_id: str,
    theme: dict,
):
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
    for i, pp in enumerate(values):
        if pp > current_best:
            personal_bests.append((i + 1, pp))
            current_best = pp

    x_best, y_best = zip(*personal_bests)
    ax.scatter(x_best, y_best, color="#53D76A", marker=".", zorder=10, s=35)
    ax.scatter(x_best[-1], y_best[-1], color="#FFB600", marker="*", zorder=15, s=35)

    ax.set_xlabel(f"Races")
    ax.set_ylabel("pp")
    title = f"pp Improvement - Quote {quote_id}"
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
