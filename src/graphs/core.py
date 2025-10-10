from datetime import datetime, timezone

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from config import ROOT_DIR
from utils import dates

ASSETS_DIR = ROOT_DIR / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "DMSans-Medium.ttf"
fm.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = fm.FontProperties(fname=FONT_PATH).get_name()

matplotlib.colormaps.register(LinearSegmentedColormap.from_list("keegan", ["#0094FF", "#FF00DC"]))


def apply_theme(ax: Axes, theme: dict):
    """Apply a theme to all graph elements."""
    # Backgrounds
    background_color = theme["background"]
    ax.figure.set_facecolor(background_color)
    ax.set_facecolor(theme["graph_background"])

    # Text
    ax.title.set_color(theme["title"])
    ax.title.set_fontsize(14)
    ax.xaxis.label.set_color(theme["text"])
    ax.yaxis.label.set_color(theme["text"])

    # Axis
    ax.tick_params(axis="both", which="both", colors=theme["axis"], labelcolor=theme["text"])
    for axis in ax.spines.values():
        axis.set_color(theme["axis"])

    # Grid
    ax.grid(color=theme["grid"], alpha=theme["grid_opacity"])

    # Lines
    if theme["line"] in plt.colormaps:
        for i, line in enumerate(ax.get_lines()):
            get_line_colormap(ax, i, theme["line"])
    elif len(ax.get_lines()) > 0:
        for line in ax.get_lines():
            line.set_color(theme["line"])

    # Legend
    legend = ax.get_legend()
    if legend:
        legend.get_frame().set_facecolor(theme["graph_background"])
        legend.get_frame().set_edgecolor(theme["axis"])
        for text in legend.get_texts():
            text.set_color(theme["text"])

    # Logo
    if "\n" in ax.get_title():
        fig = ax.figure
        fig.subplots_adjust(top=0.844)
        width, height = fig.get_size_inches()
        fig.set_size_inches(width, height + 0.22)

    logo = "logo.png" if get_luminance(*to_rgb(background_color)) <= 0.5 else "logo_dark.png"
    logo_path = ASSETS_DIR / "images" / logo
    img = mpimg.imread(logo_path)
    imagebox = OffsetImage(img, zoom=0.1)
    frameon = False
    boxprops = None

    if color_distance(background_color, "#00B5E2") <= 1:
        frameon = True
        boxprops = dict(
            facecolor="#00031B",
            edgecolor="none",
            alpha=0.25,
            boxstyle="round,pad=0.4"
        )

    ab = AnnotationBbox(
        imagebox,
        (0, 1),
        xycoords="figure fraction",
        boxcoords="offset points",
        xybox=(6, -6),
        box_alignment=(0, 1),
        frameon=frameon,
        bboxprops=boxprops
    )
    ax.figure.add_artist(ab)
    ax.add_artist(ab)


def get_line_colormap(ax: Axes, line_index: int, colormap_name: str):
    """Returns a line collection object with a colormap applied."""
    cmap = plt.get_cmap(colormap_name)
    line = ax.get_lines()[line_index]
    x, y = line.get_data()

    ax.lines[line_index].remove()
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap, zorder=50, linewidth=1.5)
    lc.set_array(np.linspace(0, 1, len(x)))
    ax.add_collection(lc)

    return lc


def interpolate_segments(x, y):
    """Returns a list of interpolated X and Y segments."""
    x_segments = []
    y_segments = []

    for i in range(len(y) - 1):
        x_range = x[-1] - x[0]
        x_difference = x[i + 1] - x[i]
        if x_difference == 0:
            continue
        x_size = x_range / x_difference
        segment_count = max(int(50 / x_size), 2)
        if segment_count == 2 and i < len(y) - 2:
            x_segments.append(x[i])
            y_segments.append(y[i])
            continue

        segments = np.linspace(y[i], y[i + 1], segment_count)
        for v in segments[:-1]:
            y_segments.append(v)

        segments = np.linspace(x[i], x[i + 1], segment_count)
        for v in segments[:-1]:
            x_segments.append(v)

    y_segments.append(y[-1])
    x_segments.append(x[-1])

    return x_segments, y_segments


def apply_date_ticks(ax: Axes, timestamps: list[float]):
    """Applies date ticks evenly spaced on the X-axis."""
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    date_range = max_timestamp - min_timestamp
    step = date_range / 5

    ticks = [min_timestamp + step * i for i in range(6)]
    labels = [datetime.fromtimestamp(ts, timezone.utc).strftime("%b %#d '%y") for ts in ticks]

    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)

    padding = date_range * 0.05
    ax.set_xlim(min_timestamp - padding, max_timestamp + padding)


def get_luminance(r, g, b):
    """Returns the luminance of RGB values."""
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def color_distance(color1, color2):
    """Returns the distance between two colors."""
    rgb1 = to_rgb(color1)
    rgb2 = to_rgb(color2)
    return np.linalg.norm(np.array(rgb1) - np.array(rgb2))


def generate_file_name(prefix: str):
    """Returns a unique file name with a prefix."""
    return f"{prefix}_{round(dates.now().timestamp() * 1000)}.png"
