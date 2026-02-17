import numpy as np
from matplotlib.collections import LineCollection

from graphs.core import plt, apply_theme, generate_file_name


def moving_average(y, window=20):
    """Computes a moving average, ignoring zero values."""
    y = np.asarray(y, dtype=float)

    if len(y) < window:
        return y

    mask = y > 0
    kernel = np.ones(window)

    sums = np.convolve(y * mask, kernel, mode="same")
    counts = np.convolve(mask.astype(float), kernel, mode="same")

    with np.errstate(divide="ignore", invalid="ignore"):
        average = np.where(counts > 0, sums / counts, np.nan)

    nans = np.isnan(average)
    if nans.any() and not nans.all():
        x = np.arange(len(average))
        average[nans] = np.interp(x[nans], x[~nans], average[~nans])

    return average


def render(
    data: list[dict],
    difficulties: list[float],
    title: str,
    theme: dict,
):
    x = np.array(range(1, len(data) + 1))
    p1_wpm = np.array([match["userWpm"] for match in data])
    p2_wpm = np.array([match["opponentWpm"] for match in data])
    difficulties = np.array(difficulties)

    fig, ax = plt.subplots()
    ax2 = ax.twinx()

    window = max(5, len(x) // 20)

    p1_avg = moving_average(p1_wpm, window)
    p2_avg = moving_average(p2_wpm, window)
    diff_avg = moving_average(difficulties, window)
    diff_x_avg = range(window, len(x) + 1) if len(diff_avg) < len(x) else x

    def plot_colored_path(ax, x_vals, y_vals, raw_wpm, base_color, zorder):
        """Create a line that becomes marked during DNFs."""
        points = np.array([x_vals, y_vals]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        colors = [
            theme["crosses"] if raw_wpm[i + 1] == 0 else base_color
            for i in range(len(x_vals) - 1)
        ]

        lc = LineCollection(segments, colors=colors, linewidth=1.5, zorder=zorder)
        ax.add_collection(lc)

    plot_colored_path(ax, x, p1_avg, p1_wpm, "#00a2ff", 333)
    plot_colored_path(ax, x, p2_avg, p2_wpm, "#af8fe9", 111)

    ax2.plot(diff_x_avg, diff_avg, color="#808080", alpha=0.5, linewidth=1)

    ax.set_xlabel("Encounter #")
    ax.set_ylabel("WPM")
    ax2.set_ylabel("Difficulty")
    ax.set_title(title)

    non_zeroes = [val for val in np.concatenate([p1_wpm, p2_wpm]) if val > 0]
    if non_zeroes:
        ax.set_ylim(min(non_zeroes) * 0.95, max(p1_avg.max(), p2_avg.max()) * 1.05)

    apply_theme(ax, theme, themed_line=99)
    apply_theme(ax2, theme | {"grid_opacity": 0})

    file = generate_file_name("encounters")
    plt.savefig(file)
    plt.close(fig)

    return file
