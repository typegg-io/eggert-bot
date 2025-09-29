from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    quotes: list[dict],
    quote_bests: list[dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]

    pp = []
    length = []

    quote_dict = {(quote := quote_data["quote"])["quoteId"]: quote for quote_data in quotes}

    for race in quote_bests:
        quote = quote_dict[race["quoteId"]]
        pp.append(race["pp"])
        length.append(len(quote["text"]))

    ax.scatter(length, pp, cmap=color, s=6)

    ax.set_title(f"pp Per Quote Length - {username}")
    ax.set_xlabel("Quote Length")
    ax.set_ylabel("pp")
    ax.set_xticks([50, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000])

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("compare")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

