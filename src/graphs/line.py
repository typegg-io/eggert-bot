from matplotlib.ticker import FuncFormatter

from graphs.core import plt, apply_theme, interpolate_segments, apply_date_ticks, generate_file_name, filter_palette
from utils.dates import get_timestamp_list
from utils.strings import format_big_number


def render(
    author_username: str,
    lines: list[dict],
    title: str,
    y_label: str,
    theme: dict,
):
    fig, ax = plt.subplots()
    filter_palette(ax, theme["line"])

    themed_line = 0
    timestamps = get_timestamp_list([timestamp for line in lines for timestamp in line["x_values"]])
    max_timestamp = max(timestamps)

    for i, line in enumerate(lines[::-1]):
        username = line["username"]
        x = line["x_values"]
        y = line["y_values"]

        # Extending lines to the end of the graph
        y.append(y[-1])
        x = get_timestamp_list(x)
        x.append(max_timestamp)

        # Downsampling
        first_x, first_y = x[0], y[0]
        last_x, last_y = x[-1], y[-1]
        if len(x) > 10000:
            x = x[::len(x) // 1000]
            y = y[::len(y) // 1000]
        x.insert(0, first_x)
        x.append(last_x)
        y.insert(0, first_y)
        y.append(last_y)

        x, y = interpolate_segments(x, y)
        ax.plot(x, y, label=username)

        if username == author_username:
            themed_line = i

    plt.grid()
    ax.set_title(title)
    ax.set_xlabel("Dates")
    ax.set_ylabel(y_label)

    apply_date_ticks(ax, timestamps)
    ax.yaxis.set_major_formatter(FuncFormatter(format_big_number))

    apply_theme(ax, theme, themed_line=themed_line)

    file_name = generate_file_name("line")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name
