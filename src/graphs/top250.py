from typing import Dict, List
from config import DEFAULT_THEME
from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    profiles: List[Dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    color = theme["line"]
    if color in plt.colormaps():
        color = DEFAULT_THEME["line"]

    for profile in profiles:
        data = profile["data"]

        if profile["username"] == username:
            ax.plot(range(1, len(data) + 1), data, color=color, label=profile["username"])
        else:
            ax.plot(range(1, len(data) + 1), data, label=profile["username"])

    ax.set_title("Top 250 pp scores")
    ax.set_xlabel("Quote Ranking")
    ax.set_ylabel("pp")

    apply_theme(ax, theme=theme, legend_loc=1)

    file_name = generate_file_name("top250")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

