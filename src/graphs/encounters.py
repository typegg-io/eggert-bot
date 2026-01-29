import numpy as np

from graphs.core import plt, apply_theme, generate_file_name


def moving_average(y, window=20):
    if len(y) < window:
        return y
    return np.convolve(y, np.ones(window) / window, mode="valid")

def render(
    data: list,
    title: str,
    theme: dict,
):
    x = range(1, len(data) + 1)
    p1_wpm = [match["userWpm"] for match in data]
    p2_wpm = [match["opponentWpm"] for match in data]

    fig, ax = plt.subplots()

    ax.scatter(x, p2_wpm, color="#55ACEE", s=2)
    ax.scatter(x, p1_wpm, color="#DD2E44", s=2)

    if len(x) > 1:
        window = max(5, len(x) // 20)

        r1_avg = moving_average(p1_wpm, window)
        r2_avg = moving_average(p2_wpm, window)

        x_avg = range(window, len(x) + 1)

        ax.plot(x_avg, r2_avg, color=theme["graph_background"], linewidth=4)
        ax.plot(x_avg, r2_avg, color="#55ACEE", linewidth=1.5)

        ax.plot(x_avg, r1_avg, color=theme["graph_background"], linewidth=4)
        ax.plot(x_avg, r1_avg, color="#DD2E44", linewidth=1.5)

    ax.set_xlabel("Encounter #")
    ax.set_ylabel("WPM")
    ax.set_title(title)

    apply_theme(ax, theme, themed_line=99)

    file = generate_file_name("encounters")
    plt.savefig(file)
    plt.close(fig)

    return file