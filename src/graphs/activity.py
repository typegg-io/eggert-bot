"""The daily clock and weekly bar graphs of when a user races."""

import numpy as np
from matplotlib import patches
from matplotlib.ticker import FuncFormatter

from graphs.core import apply_theme, generate_file_name, plt
from utils.schemas import Theme
from utils.strings import format_big_number

DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SAMPLES_PER_HOUR = 50


def render_clock(username: str, counts: list[int], offset: str, theme: Theme) -> str:
    """Render races by hour of the day around a clock face and return the file name."""
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)

    width = 2 * np.pi / len(counts)
    hours = np.arange(len(counts)) * width

    if theme["line"] in plt.colormaps():
        apply_clock_colormap(ax, counts, theme)
    else:
        # An hour's bar covers the hour it opens, so its center sits half an hour clockwise.
        ax.bar(hours + width / 2, counts, width=width, color=theme["line"])

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(hours)
    ax.set_xticklabels([str(hour) for hour in range(len(counts))])
    ax.set_yticks([])
    ax.set_title(f"Daily Activity ({offset}) - {username}")

    apply_theme(ax, theme)

    file_name = generate_file_name("activity")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_clock_colormap(ax, counts: list[int], theme: Theme) -> None:
    """Fill every hour's wedge with the colormap, spending it from the center outwards."""
    peak = max(counts) * 1.05
    reach = np.repeat(counts, SAMPLES_PER_HOUR) / peak

    theta_edges = np.linspace(0, 2 * np.pi, len(reach) + 1)
    radii = np.linspace(0, 1, 300)
    theta_grid, radius_grid = np.meshgrid(theta_edges, radii)

    # Masked cells are never drawn, which leaves the graph background showing beyond each wedge.
    mesh = np.ma.masked_array(radius_grid, radius_grid > np.append(reach, reach[-1]))
    ax.pcolormesh(theta_grid, radius_grid, mesh, cmap=plt.get_cmap(theme["line"]), shading="auto")

    width = 2 * np.pi / len(counts)
    ax.bar(
        np.arange(len(counts)) * width + width / 2,
        np.array(counts) / peak,
        width=width,
        bottom=0,
        edgecolor=theme["graph_background"],
        facecolor="none",
        linewidth=0.1,
    )


def render_weekly(username: str, counts: list[int], offset: str, theme: Theme) -> str:
    """Render races by day of the week as bars and return the file name."""
    fig, ax = plt.subplots()

    days = list(range(len(counts)))
    y_limit = max(counts) * 1.05

    if theme["line"] in plt.colormaps():
        apply_weekly_colormap(ax, days, counts, theme, y_limit)
    else:
        ax.bar(days, counts, color=theme["line"])

    ax.set_ylim(0, y_limit)
    ax.set_xticks(days)
    ax.set_xticklabels(DAY_LABELS)
    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))
    ax.set_ylabel("Races")
    ax.set_title(f"Weekly Activity ({offset}) - {username}")

    apply_theme(ax, theme)

    file_name = generate_file_name("activity")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name


def apply_weekly_colormap(ax, days: list[int], counts: list[int], theme: Theme, y_limit: float) -> None:
    """Fill every day's bar with the colormap, spending it from the axis upwards."""
    background = theme["graph_background"]
    bars = ax.bar(days, counts, alpha=0)
    bar_width = bars[0].get_width()

    gradient = np.linspace(0, 10, 100).reshape(-1, 1)
    extent = [ax.get_xlim()[0], ax.get_xlim()[1], 0, max(counts)]
    ax.imshow(gradient, cmap=plt.get_cmap(theme["line"]), extent=extent, origin="lower", aspect="auto")
    ax.set_ylim(0, y_limit)

    for bar in bars:
        ax.add_patch(patches.Rectangle(
            (bar.get_x(), bar.get_height()),
            bar_width,
            y_limit - bar.get_height(),
            color=background,
        ))

    for day, next_day in zip(days, days[1:], strict=False):
        left = day + bar_width / 2
        ax.add_patch(patches.Rectangle(
            (left, 0), next_day - bar_width / 2 - left, y_limit, color=background,
        ))

    x_min, x_max = ax.get_xlim()
    ax.add_patch(patches.Rectangle(
        (x_min, 0), days[0] - bar_width / 2 - x_min, y_limit, color=background,
    ))
    ax.add_patch(patches.Rectangle(
        (days[-1] + bar_width / 2, 0), x_max - days[-1] - bar_width / 2, y_limit, color=background,
    ))
