import sys
import textwrap
from datetime import datetime, timezone
from typing import Optional

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.legend_handler import HandlerLine2D, HandlerLineCollection
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

from config import ROOT_DIR
from utils import dates

ASSETS_DIR = ROOT_DIR / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "DMSans-Medium.ttf"
fm.fontManager.addfont(FONT_PATH)
plt.rcParams["font.family"] = fm.FontProperties(fname=FONT_PATH).get_name()

GRAPH_PALETTE = [
    "#00AAD6", "#E41A1C", "#118011", "#FF7F00", "#7C3AFF",
    "#FCD500", "#F781BF", "#A65628", "#43B187", "#999999",
    "#BCBD22",
]
plt.rcParams["axes.prop_cycle"] = plt.cycler(color=GRAPH_PALETTE)

matplotlib.colormaps.register(LinearSegmentedColormap.from_list("plus", ["#4c0c39", "#FF27BE"]))
matplotlib.colormaps.register(LinearSegmentedColormap.from_list("keegan", ["#0094FF", "#FF00DC"]))


class LineHandler(HandlerLine2D):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        line = plt.Line2D([0, 21], [3.5, 3.5], color=orig_handle.get_color())
        return [line]


class CollectionHandler(HandlerLineCollection):
    def create_artists(self, legend, artist, xdescent, ydescent, width, height, fontsize, trans):
        x = np.linspace(0, width, self.get_numpoints(legend) + 1)
        y = np.zeros(self.get_numpoints(legend) + 1) + height / 2. - ydescent
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=artist.cmap, transform=trans)
        lc.set_array(x)
        return [lc]


def apply_theme(
    ax: Axes, theme: dict,
    legend_loc: Optional[int | str] = "upper left",
    force_legend: bool = False,
    themed_line: int = 0,
):
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

    # Lines & Legend
    legend_lines, legend_labels, handler_map = [], [], {}
    line_color = theme["line"]

    for i, line in enumerate(ax.get_lines()):
        label = line.get_label()
        if label.startswith("_child"):
            continue

        label = "-\n".join(textwrap.wrap(label, width=18))
        # if label.startswith("_"):
        #     label = "\u200B" + label

        if label in ["Raw Speed"]:
            line.set_color(theme["raw_speed"])
            line.set_linewidth(1)

        line_handler = LineHandler()

        if i == themed_line:
            if line_color in plt.colormaps():
                line = get_line_colormap(ax, i, line_color)
                line_handler = CollectionHandler(numpoints=50)
            else:
                line.set_color(line_color)

        legend_lines.append(line)
        legend_labels.append(label)
        handler_map[line] = line_handler

    if len(legend_lines) > 1 or force_legend:
        legend_kwargs = {
            "handles": legend_lines,
            "labels": legend_labels,
            "handler_map": handler_map,
            "loc": legend_loc
        }
        caller_file = sys._getframe(1).f_code.co_filename

        if any(graph in caller_file for graph in ["race", "daily", "match"]):
            legend_kwargs.update({
                "bbox_to_anchor": (1.03, 1),
                "borderaxespad": 0,
                "handletextpad": 0.5
            })
            ax.set_position([0.1, 0.1, 0.6, 0.78])
        else:
            legend_kwargs["framealpha"] = 0.5

        ax.legend(**legend_kwargs)

    legend = ax.get_legend()
    if legend:
        frame = legend.get_frame()
        frame.set_facecolor(theme["graph_background"])
        frame.set_edgecolor(theme["axis"])
        for text in legend.get_texts():
            text.set_color(theme["text"])

    # TypeGG Logo
    if "\n" in ax.get_title():
        fig = ax.figure
        fig.subplots_adjust(top=0.844)
        width, height = fig.get_size_inches()
        fig.set_size_inches(width, height + 0.22)

    logo = "logo.png" if get_luminance(*to_rgb(background_color)) <= 0.5 else "logo_dark.png"
    logo_path = ASSETS_DIR / "images" / logo
    img = mpimg.imread(logo_path)
    imagebox = OffsetImage(img, zoom=0.55)
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

    # GG+ Badge
    if theme.get("isGgPlus"):
        plus_path = ASSETS_DIR / "images" / "plus.png"
        plus_img = mpimg.imread(plus_path)
        plus_imagebox = OffsetImage(plus_img, zoom=0.045)

        plus_ab = AnnotationBbox(
            plus_imagebox,
            (1, 1),
            xycoords="figure fraction",
            boxcoords="offset points",
            xybox=(-6, -6),
            box_alignment=(1, 1),
            frameon=False
        )
        ax.figure.add_artist(plus_ab)
        ax.add_artist(plus_ab)


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


def filter_palette(ax: Axes, line_color: str):
    """Filters the current graph palette to avoid color clashing with a line color."""
    if line_color in plt.colormaps():
        return

    ax.set_prop_cycle(plt.cycler(color=[
        color for color in GRAPH_PALETTE
        if color_distance(line_color, color) > 0.25
    ]))
