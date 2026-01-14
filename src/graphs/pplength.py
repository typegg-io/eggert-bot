from graphs.core import plt, apply_theme, generate_file_name, filter_palette, apply_log_ticks
from utils.strings import format_big_number


def render(
    title: str,
    quotes: list[dict],
    quote_bests: list[dict],
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
        length.append(local_length)

        if local_length > max_length:
            max_length = local_length

    if color in plt.colormaps():
        ax.scatter(length, pp, s=6, c=pp, cmap=color)
    else:
        ax.scatter(length, pp, s=6, color=color)

    apply_log_ticks(ax, max_length)
    ax.xaxis.set_major_formatter(format_big_number)

    ax.set_title(title)
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("pp")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("pplength")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
