from graphs.core import plt, apply_theme, generate_file_name


def render(theme: dict):
    x = [i for i in range(100)]
    y = x

    x2 = [i for i in range(50)]
    y2 = [i + 50 for i in x2]

    ax = plt.subplots()[1]
    ax.plot(x, y, label="Data")
    ax.plot(x2, y2, label="Raw Speed", color=theme["raw_speed"], zorder=10)
    plt.grid()

    ax.set_title("Sample Graph")
    ax.set_xlabel("X-Axis")
    ax.set_ylabel("Y-Axis")

    apply_theme(ax, theme)

    file_name = generate_file_name("sample")
    plt.savefig(file_name)
    plt.close()

    return file_name
