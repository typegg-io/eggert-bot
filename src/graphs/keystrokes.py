from typing import List, Dict

import matplotlib.colors as mcolors
import matplotlib.patches as patches
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from graphs.core import plt, generate_file_name
from utils.keyboard_layouts import K
from utils.strings import format_big_number


def render(
    username: str,
    keyboard_layout: str,
    keypresses: Dict[str, int],
    keymap: List[List[K]],
    theme: dict,
):
    colors = [
        (0, "#FFEA8C"),
        (0.2, "#FFBE0B"),
        (0.5, "#FB5607"),
        (1, "#D00000"),
    ]
    bg_color = theme["background"]
    text_color = theme["text"]

    cmap = LinearSegmentedColormap.from_list("yellow_orange_red", colors)
    unused_color = "lightgray"

    fig, ax = plt.subplots(constrained_layout=True)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    max_presses = 0
    rectangles = []
    shift_presses = 0
    alt_presses = 0

    for row_i, row in enumerate(keymap):
        total_width = 0

        for key in row:
            total_presses = 0

            for i, character in enumerate(key.matches):
                if character not in keypresses:
                    continue

                presses = keypresses[character]
                total_presses += presses

                if i == 1:
                    shift_presses += presses
                elif i == 2:
                    alt_presses += presses
                elif i == 3:
                    shift_presses += presses
                    alt_presses += presses

            if total_presses > max_presses:
                max_presses = total_presses

            square = patches.Rectangle((total_width, -row_i), key.width, 1, edgecolor="black")
            ax.text(total_width + key.width / 2, 0.5 - row_i, key.text, ha="center", va="center", fontsize=key.fontsize, color="black")

            if key.text == "Shift":
                total_presses = -1
            elif key.text == "Alt":
                total_presses = -2

            rectangles.append((square, total_presses))
            total_width += key.width

    for rectangle, presses in rectangles:
        if presses == -1:
            presses = shift_presses
        elif presses == -2:
            presses = alt_presses

        if presses == 0:
            rectangle.set_facecolor(unused_color)
        else:
            rectangle.set_facecolor(cmap(presses / max_presses))

        ax.add_patch(rectangle)

    plt.xlim(-0.1, 15.1)
    plt.ylim(-4.1, 1.1)
    plt.axis("off")
    plt.title(f"Keystroke Heatmap - {username} - {keyboard_layout.upper()}", pad=10, fontsize=16, color=text_color)
    plt.gca().set_aspect("equal", adjustable="box")

    sm = cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=0, vmax=max_presses))
    sm.set_array([])
    cbar_width = 0.8
    cbar_height = 0.04
    cbar_ax = fig.add_axes([0.5 - cbar_width / 2, 0.18, cbar_width, cbar_height])
    cbar_ax.set_facecolor(bg_color)

    cbar = plt.colorbar(sm, cax=cbar_ax, orientation="horizontal")
    cbar.set_label("Key Presses", labelpad=2, fontsize=12, color=text_color)
    cbar.ax.xaxis.set_major_formatter(FuncFormatter(format_big_number))
    cbar.ax.tick_params(axis="x", colors=text_color, labelsize=11)
    cbar.ax.xaxis.label.set_y(-1.5)

    fig.set_constrained_layout_pads(w_pad=0.05, h_pad=0.05, hspace=0.05, wspace=0.05)

    file_name = generate_file_name("keystrokes")

    plt.savefig(file_name, bbox_inches="tight", pad_inches=0.15, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    return file_name
