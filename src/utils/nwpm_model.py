import json
from bisect import bisect_left

from api.leaders import get_leaders
from config import SOURCE_DIR
from utils.logging import log

DATA_FILE = SOURCE_DIR / "data" / "pp_nwpm.json"

try:
    with open(DATA_FILE, "r") as f:
        if not f.read().strip():
            raise FileNotFoundError
except FileNotFoundError:
    with open(DATA_FILE, "w") as f:
        f.write("[]")

nwpm_data = []  # Local copy of [pp, nWPM] data


async def update_nwpm_data():
    """Update the pp nWPM point data used for calculating nWPM."""
    log("Updating pp nWPM points")

    with open(DATA_FILE, "r") as f:
        raw = f.read().strip() or "[]"
        data = json.loads(raw)

    for sort in ["totalPp", "nWpm", "quotesTyped"]:
        log(f"Fetching leaders (sort = {sort})")
        for i in range(10):
            log(f"Page {i + 1} / 10")
            leaders = await get_leaders(per_page=100, page=i + 1, sort=sort)
            for leader in leaders["users"]:
                if leader["stats"]["quotesTyped"] < 125:
                    continue

                data.append([leader["stats"]["nWpm"], leader["stats"]["totalPp"]])

    log("Cleaning data")
    clean_data = clean_nwpm_data(data)

    with open(DATA_FILE, "w") as f:
        json.dump(clean_data, f)

    log("Finished updating pp nWPM points")


def clean_nwpm_data(data: list):
    """Remove points that violate monotonicity (higher pp should always = higher nWPM)."""
    data.sort(key=lambda x: x[0])
    clean = []
    max_nwpm = float("-inf")

    for pp, nwpm in data:
        if nwpm > max_nwpm:
            clean.append((pp, nwpm))
            max_nwpm = nwpm

    return clean


def load_local_data():
    """Load the JSON data to a local variable."""
    global nwpm_data

    with open(DATA_FILE, "r") as f:
        raw = f.read().strip()
        nwpm_data = json.loads(raw)


async def initialize_nwpm_model():
    """Initialize the nWPM model, fetching data if empty."""
    load_local_data()

    if not nwpm_data:
        log("nWPM data is empty. Fetching data from leaderboards...")
        await update_nwpm_data()
        load_local_data()


def _interpolate(x, x0, y0, x1, y1):
    """Simple linear interpolation."""
    if x1 == x0:
        return 0.5 * (y0 + y1)
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


def calculate_nwpm(total_pp: float):
    """Estimate nWPM from a given PP value using linear interpolation."""
    pp_values, _ = zip(*nwpm_data)
    idx = bisect_left(pp_values, total_pp)

    # Below range -> extrapolate from first two points
    if idx == 0:
        pp0, nw0 = nwpm_data[0]
        pp1, nw1 = nwpm_data[1]

    # Above range -> extrapolate from last two points
    elif idx >= len(nwpm_data):
        pp0, nw0 = nwpm_data[-2]
        pp1, nw1 = nwpm_data[-1]

    # Inside range -> interpolate between neighbors
    else:
        pp0, nw0 = nwpm_data[idx - 1]
        pp1, nw1 = nwpm_data[idx]

    return _interpolate(total_pp, pp0, nw0, pp1, nw1)
