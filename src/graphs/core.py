import os

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

def apply_theme(ax: Axes, theme: dict):
    # Backgrounds
    ax.figure.set_facecolor(theme["background"])
    ax.set_facecolor(theme["graph_background"])

    # Text
    ax.title.set_color(theme["text"])
    # ax.set_title(label=ax.get_title(), color=theme["text"])
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

    # Line
    ax.get_lines()[0].set_color(theme["line"])

    pass

def remove_file(file_name: str):
    try:
        os.remove(file_name)
    except FileNotFoundError:
        print("File not found.")