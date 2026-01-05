from numpy import append, power, log as np_log
from graphs.core import plt, apply_theme, generate_file_name, filter_palette
from math import log
from matplotlib.ticker import MaxNLocator
from utils.prettify_xticks import prettyfyLengthXticks


def render(
    username: str,
    wpm: list[float],
    length: list[int],
    log_base: int,
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    filter_palette(ax, color)

    ax.step(length, wpm, color=color, where="pre")

    ax.set_title(f"WPM PB Per Quote Length - {username}")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("WPM")

    ax.xaxis.set_major_locator(MaxNLocator(nbins=11))  # Needs to be odd if you want to include the start and end xtick
    xticks = ax.get_xticks()
    xticks = append(xticks[:-1], log(max(length), log_base))  # Make the max xtick equal to the max length
    xticks = power(log_base, xticks)
    xticks = np_log(prettyfyLengthXticks(xticks)) / np_log(log_base)

    ax.set_xticks(xticks)

    ax.set_xticklabels([f"{xtick:.0f}" for xtick in log_base ** ax.get_xticks()])

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("endurance")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

