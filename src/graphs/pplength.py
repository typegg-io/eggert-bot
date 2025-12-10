from graphs.core import plt, apply_theme, generate_file_name, filter_palette


def render(
    username: str,
    quotes: list[dict],
    quote_bests: list[dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    filter_palette(ax, color)

    pp = []
    length = []

    for race in quote_bests:
        quote = quotes[race["quoteId"]]
        pp.append(race["pp"])
        length.append(len(quote["text"]))

    if color in plt.colormaps():
        ax.scatter(length, pp, s=6, c=pp, cmap=color)
    else:
        ax.scatter(length, pp, s=6, color=color)

    ax.set_title(f"pp Per Quote Length - {username}")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("pp")

    max_length = max(length)
    intervals = [50, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000]
    intervals = [i for i in intervals if i <= max_length]
    ax.set_xticks(intervals)

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("pplength")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
