from graphs.core import plt, apply_theme, generate_file_name, filter_palette
from math import log
from matplotlib.ticker import MaxNLocator
from utils.prettify_xticks import prettyfyLengthXticks
from numpy import append, power, log as np_log


def render(
    username: str,
    quotes: list[dict],
    quote_bests: list[dict],
    log_base: int,
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    filter_palette(ax, color)

    pp = []
    length = []
    max_length = 0

    for race in quote_bests:
        quote = quotes[race["quoteId"]]
        pp.append(race["pp"])
        local_length = len(quote["text"])
        length.append(log(local_length, log_base))

        if local_length > max_length:
            max_length = local_length

    if color in plt.colormaps():
        ax.scatter(length, pp, s=6, c=pp, cmap=color)
    else:
        ax.scatter(length, pp, s=6, color=color)

    ax.xaxis.set_major_locator(MaxNLocator(nbins=11))  # Needs to be odd if you want to include the start and end xtick
    xticks = ax.get_xticks()
    xticks = append(xticks[:-1], log(max_length, log_base))  # Make the max xtick equal to the max length
    xticks = power(log_base, xticks)
    xticks = np_log(prettyfyLengthXticks(xticks)) / np_log(log_base)

    ax.set_xticks(xticks)

    ax.set_xticklabels([f"{xtick:.0f}" for xtick in log_base ** ax.get_xticks()])

    ax.set_title(f"pp Per Quote Length - {username}")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("pp")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("pplength")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
