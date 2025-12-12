from graphs.core import plt, generate_file_name
from typing import List, Dict
import matplotlib.patches as patches
from matplotlib import cm
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from utils.keyboard_layouts import K


def render(
    username: str,
    keyboard_layout: str,
    keypresses: Dict[str, int],
    keymap: List[List[K]]
):
    colors = [
        (0, "lightgray"),
        (0.1, "yellow"),
        (0.3, "orange"),
        (0.7, "red"),
        (1, "darkred"),
    ]

    cmap = LinearSegmentedColormap.from_list("blue_yellow_orange_red", colors)
    fig, ax = plt.subplots(constrained_layout=True)

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

                if i == 2:
                    alt_presses += presses

            if total_presses > max_presses:
                max_presses = total_presses

            square = patches.Rectangle((total_width, -row_i), key.width, 1, edgecolor="black")
            ax.text(total_width + key.width / 2, 0.5 - row_i, key.text, ha="center", va="center", fontsize=key.fontsize)

            if key.text == "Shift":
                total_presses = -1

            if key.text == "Alt":
                total_presses = -2

            rectangles.append((square, total_presses))
            total_width += key.width

    for rectangle, presses in rectangles:
        if presses == -1:
            presses = shift_presses
        elif presses == -2:
            presses = alt_presses

        rectangle.set_facecolor(cmap(presses/max_presses))
        ax.add_patch(rectangle)

    plt.xlim(-0.1, 15.1)
    plt.ylim(-4.1, 1.1)
    plt.axis('off')
    plt.title(f"Keystroke heatmap of {username} in {keyboard_layout}")
    plt.gca().set_aspect("equal", adjustable="box")

    # Cmap legend
    sm = cm.ScalarMappable(cmap=cmap, norm=mcolors.Normalize(vmin=0, vmax=max_presses))
    sm.set_array([])
    cbar_width = 0.8
    cbar_height = 0.04
    cbar_ax = fig.add_axes([0.5 - cbar_width / 2, 0.15, cbar_width, cbar_height])
    cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal')
    cbar.set_label('Key Presses')

    file_name = generate_file_name("keystrokes")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

