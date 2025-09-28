from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    quotes: list[dict],
    races: list[dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]

    pp = []
    length = []

    for race in races:
        for quote in quotes:
            quote = quote["quote"]

            if quote["quoteId"] == race["quoteId"] and (new_pp := race["pp"]) > 0:
                pp.append(new_pp)
                length.append(len(quote["text"]))

    ax.scatter(length, pp, cmap=color, s=6)

    ax.set_title(f"PP per quote length - {username}")
    ax.set_xlabel("quote length")
    ax.set_ylabel("PP")
    ax.set_xticks([50, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000])

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("compare")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

