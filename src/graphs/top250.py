from typing import Set
from graphs.core import plt, apply_theme, generate_file_name


def render(
    profiles: Set[dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]

    for profile in profiles:
        pp = list(map(lambda data: data["pp"], profile))

        if color in plt.colormaps():
            ax.plot(range(1, len(pp)), pp, cmap=color, label=profile["username"])
        else:
            ax.plot(range(1, len(pp)), pp, color=color)

    ax.set_title("Top 250 pp scores")
    ax.set_xlabel("Quote Ranking")
    ax.set_ylabel("pp")

    apply_theme(ax, theme=theme)

    file_name = generate_file_name("top250")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

