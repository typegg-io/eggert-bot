from typing import Dict, List
from config import DEFAULT_THEME
from graphs.core import plt, apply_theme, generate_file_name
import numpy as np
from numpy.typing import NDArray
import matplotlib.dates as mdates
from pandas import to_datetime
from datetime import datetime


def calculateTotal(values: NDArray[float]):
    values = np.array(sorted(values, reverse=True))
    multiply = np.array([0.97 ** i for i in range(0, len(values))])
    total_pp = (values * multiply)
    total_pp[total_pp < 1] = 0

    return sum(total_pp)


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
        timestamps = []
        values = []
        pb_dict = {}

        for datapoint in data:
            id = datapoint["quoteId"]
            pp = datapoint["pp"]
            timestamp = to_datetime(datapoint["timestamp"], utc=True)
            should_recalculate = False

            if id in pb_dict:
                if pb_dict[id] < pp:
                    pb_dict[id] = pp
                    should_recalculate = True
            else:
                pb_dict[id] = pp
                should_recalculate = True

            if should_recalculate:
                total_pp = calculateTotal(sorted(pb_dict.values(), reverse=True)[:250])

                if len(values) == 0 or total_pp > values[-1]:
                    timestamps.append(timestamp)
                    values.append(total_pp)

        if len(values) > 0:
            timestamps.append(datetime.now())
            values.append(values[-1])

        if profile["username"] == username:
            ax.plot(timestamps, values, color=color, label=profile["username"])
        else:
            ax.plot(timestamps, values, label=profile["username"])

    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m %Y'))

    plt.xticks(rotation=90)
    plt.title("Total pp progression")
    plt.xlabel("date")
    plt.ylabel("pp")

    ax.legend()
    plt.tight_layout()
    apply_theme(ax, theme=theme, legend_loc=4)

    file_name = generate_file_name("pp_totals")
    plt.savefig(file_name)
    plt.close(fig)

    return file_name

