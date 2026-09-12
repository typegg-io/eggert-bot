"""The daily clock and weekly bar graphs of when a user races."""

import numpy as np
from matplotlib.ticker import FuncFormatter

from graphs.core import apply_theme, generate_file_name, plt
from utils.schemas import Theme
from utils.strings import format_big_number

DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def bar_colors(bars: int, theme: Theme) -> list | str:
    """Return the color of every bar, spending a colormap across the periods the graph covers."""
    color = theme["line"]
    if color not in plt.colormaps():
        return color

    # Spending the map by height instead would leave a quiet period too dark to see.
    cmap = plt.get_cmap(color)

    return [cmap(i / (bars - 1)) for i in range(bars)]


def render_clock(username: str, counts: list[int], timezone: str, theme: Theme) -> str:
    """Render races by hour of the day around a clock face and return the file name."""
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)

    width = 2 * np.pi / len(counts)
    hours = np.arange(len(counts)) * width
    # An hour's bar covers the hour it opens, so its center sits half an hour clockwise.
    ax.bar(hours + width / 2, counts, width=width, color=bar_colors(len(counts), theme))

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(hours)
    ax.set_xticklabels([str(hour) for hour in range(len(counts))])
    ax.set_yticks([])
    ax.set_title(f"Daily Activity ({timezone}) - {username}")

    apply_theme(ax, theme)

    file_name = generate_file_name("activity")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def render_weekly(username: str, counts: list[int], timezone: str, theme: Theme) -> str:
    """Render races by day of the week as bars and return the file name."""
    fig, ax = plt.subplots()

    days = range(len(counts))
    ax.bar(days, counts, color=bar_colors(len(counts), theme))

    ax.set_xticks(list(days))
    ax.set_xticklabels(DAY_LABELS)
    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_ylabel("Races")
    ax.set_title(f"Weekly Activity ({timezone}) - {username}")

    apply_theme(ax, theme)

    file_name = generate_file_name("activity")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
