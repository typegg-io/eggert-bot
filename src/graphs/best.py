from graphs.core import plt, apply_theme

def render(file_name: str, theme: dict, top_quotes: list[dict], title: str):
    plt.rcParams.update({"font.size": 18})
    ax = plt.subplots(figsize=(16, 9))[1]

    ranks = [i + 1 for i in range(len(top_quotes))]
    pp = [quote["pp"] for quote in top_quotes]
    ax.plot(ranks, pp)

    ax.set_title(title, fontsize=100)

    apply_theme(ax, theme)

    plt.savefig(file_name)