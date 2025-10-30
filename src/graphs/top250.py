from typing import Dict, List

from graphs.core import plt, apply_theme, generate_file_name


def render(
    username: str,
    profiles: List[Dict],
    theme: dict,
):
    fig, ax = plt.subplots()
    themed_line = 0

    for i, profile in enumerate(profiles):
        pp_values = profile["pp_values"]

        if profile["username"] == username:
            themed_line = i

        ax.plot(range(1, len(pp_values) + 1), pp_values, label=profile["username"])

    ax.set_title("Top 250 pp Scores")
    ax.set_xlabel("Quote Rank")
    ax.set_ylabel("pp")

    apply_theme(
        ax,
        theme=theme,
        legend_loc=1,
        force_legend=True,
        themed_line=themed_line
    )

    file_name = generate_file_name("top250")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
