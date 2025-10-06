from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    metric: str,
    quote_bests_stats: list[float],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]

    if color in plt.colormaps():
        ax.hist(quote_bests_stats, cmap=color)
    else:
        ax.hist(quote_bests_stats, color=color)

    ax.set_title(f"{metric} histogram - {username}")
    ax.set_xlabel(f"{metric}")
    ax.set_ylabel("Occurences")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("histogram")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
