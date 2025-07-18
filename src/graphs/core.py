import os
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

cmap_keegant = LinearSegmentedColormap.from_list("keegant", ["#0094FF", "#FF00DC"])
matplotlib.colormaps.register(cmap_keegant)

def apply_theme(ax: Axes, theme: dict):
    # Backgrounds
    ax.figure.set_facecolor(theme["background"])
    ax.set_facecolor(theme["graph_background"])

    # Text
    ax.title.set_color(theme["text"])
    ax.xaxis.label.set_color(theme["text"])
    ax.yaxis.label.set_color(theme["text"])

    # Axis
    ax.tick_params(axis="both", which="both", colors=theme["axis"], labelcolor=theme["text"])
    for axis in ax.spines.values():
        axis.set_color(theme["axis"])

    # Grid
    if theme["grid"] is None:
        ax.grid(False)
    else:
        ax.grid(color=theme["grid"])

    if 'line' in theme and theme['line'] in plt.colormaps():
        for i, line in enumerate(ax.get_lines()):
            # Skip lines with special labels or no data
            if not line.get_visible() or str(line.get_label()).startswith('_'):
                continue
            apply_colormap_to_line(ax, i, theme['line'])
    elif len(ax.get_lines()) > 0:
        for line in ax.get_lines():
            if not str(line.get_label()).startswith('_'):
                line.set_color(theme["line"])

def apply_colormap_to_line(ax, line_index, colormap_name):
    """Apply a colormap to a specific line in the plot"""
    if line_index >= len(ax.get_lines()):
        return None

    cmap = plt.get_cmap(colormap_name)
    line_width = 2 if colormap_name == "keegant" else 1.5

    line = ax.get_lines()[line_index]
    x, y = line.get_data()

    if len(x) < 2 or len(y) < 2:
        return None

    ax.lines[line_index].remove()

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap, zorder=50, linewidth=line_width) # type: ignore
    lc.set_array(np.linspace(0, 1, len(x)))

    ax.add_collection(lc)
    return lc


def color_graph(ax, user, recolored_line=0, force_legend=False, match=False):
    colors = user["colors"]

    ax.set_facecolor(colors["graphbackground"])
    ax.figure.set_facecolor(colors["background"])

    for axis in ax.spines.values():
        axis.set_color(colors["axis"])

    ax.set_title(label=ax.get_title(), color=colors["text"])
    ax.xaxis.label.set_color(color=colors["text"])
    ax.yaxis.label.set_color(color=colors["text"])
    ax.tick_params(axis="both", which="both", colors=colors["axis"], labelcolor=colors["text"])

    if colors["grid"] == "off":
        ax.grid(False)
    else:
        ax.grid(color=colors["grid"])

    legend_lines = []
    legend_labels = []
    handler_map = {}
    line_color = colors["line"]

    if len(ax.get_lines()) > 0:
        for i, line in enumerate(ax.get_lines()):
            label = line.get_label()

            if label.startswith("_"):
                continue

            if i == recolored_line and line_color in plt.colormaps():
                line = get_line_cmap(ax, recolored_line, user)
            elif i == recolored_line:
                line.set_color(line_color)

            if not label.startswith("_child"):
                legend_lines.append(line)
                legend_labels.append(label)

    if (len(legend_lines) > 1 or force_legend) and legend_lines:
        if match:
            legend = ax.legend(
                legend_lines, legend_labels, handler_map=handler_map, loc="upper left",
                bbox_to_anchor=(1.03, 1), borderaxespad=0, handletextpad=0.5
            )
            ax.set_position([0.1, 0.1, 0.6, 0.8])
        else:
            legend = ax.legend(
                legend_lines, legend_labels, handler_map=handler_map, loc="upper left", framealpha=0.5
            )

        legend.get_frame().set_facecolor(colors["graphbackground"])
        legend.get_frame().set_edgecolor(colors["axis"])
        for text in legend.get_texts():
            text.set_color(colors["text"])

def get_line_cmap(ax, line_index, user):
    line_width = 2 if user["colors"]["line"] == "keegant" else 1
    cmap = plt.get_cmap(user["colors"]["line"])

    if line_index >= len(ax.get_lines()):
        return None

    line = ax.get_lines()[line_index]
    x, y = line.get_data()

    ax.lines[line_index].remove()

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, cmap=cmap, zorder=50, linewidth=line_width) # type: ignore
    lc.set_array(x)

    ax.add_collection(lc)

    return lc

def apply_cmap(ax, user, counts, groups, extent):
    """
    Apply colormap to histogram bars by creating a masked gradient background

    Args:
        ax: Matplotlib axes to style
        user: User dict containing color preferences
        counts: Bar heights/widths
        groups: Bar positions
        extent: The extent of the gradient background [left, right, bottom, top]
    """
    if not counts or not groups.size:
        return

    cmap = plt.get_cmap(user["colors"]["line"])

    mask = np.zeros((len(groups) + 1, 2))
    mask[:, 0] = np.concatenate([groups, [groups[-1] if len(groups) > 0 else 0]])
    mask[:-1, 1] = counts if len(counts) > 0 else []

    for patch in ax.patches:
        patch.set_alpha(0)

    original_xlim = ax.get_xlim()

    x = np.linspace(0, 10, 100)
    y = np.linspace(0, 10, 100)
    X, Y = np.meshgrid(x, y)

    ax.imshow(X, cmap=cmap, extent=extent, origin="lower", aspect="auto")
    ax.set_xlim(original_xlim)

    graph_background = user["colors"]["graphbackground"]

    ax.fill_betweenx(mask[:, 0], mask[:, 1], extent[1], color=graph_background, step='post')

    if len(groups) > 0:
        ax.fill_betweenx([extent[2], groups[0]], [0, 0], [extent[1], extent[1]], color=graph_background)
        ax.fill_betweenx([groups[-1], extent[3]], [0, 0], [extent[1], extent[1]], color=graph_background)

def remove_file(file_name: str):
    """Remove a file if it exists"""
    try:
        os.remove(file_name)
    except FileNotFoundError:
        print("File not found.")
