"""The nWPM v3 model, a port of typegg's leaderboard model.

nWPM is the higher of two legs, shown only once the user has best races on
`CALIBRATION_MIN_QUOTES` distinct ranked English quotes:

    leg A  best mean of `WINDOW` consecutive quickplay races, each difficulty-adjusted
    leg B  a linear bridge off the median of best_wpm / predictedWpm across ranked English quotes

Parameters load from the private src/data/nwpm_params.json.

The monotonic lock lives in that package's assemble.go, not here, so a value from this
module may fall.
"""

import bisect

# Constants

REF_PWPM = None
ADJ_CLIP_LO = None
ADJ_CLIP_HI = None
WINDOW = None
CALIBRATION_MIN_QUOTES = 50
NWPM_BRIDGE_A = None
NWPM_BRIDGE_B = None


def adjust_race_wpm(wpm: float, predicted_wpm: float) -> float:
    """Return a race's WPM normalized against the reference quote difficulty."""
    if predicted_wpm <= 0:
        return wpm

    return wpm * min(max(REF_PWPM / predicted_wpm, ADJ_CLIP_LO), ADJ_CLIP_HI)


def median(values: list[float]) -> float:
    """Return the median of a sorted list, averaging the middle pair when the count is even."""
    count = len(values)
    if count == 0:
        return 0.0
    if count % 2 == 1:
        return values[count // 2]

    return 0.5 * (values[count // 2 - 1] + values[count // 2])


class QPWindow:
    """The best mean over any WINDOW consecutive quickplay races, tracked in O(1) per race."""

    def __init__(self) -> None:
        """Start an empty window."""
        self.ring: list[float] = []
        self.total = 0.0
        self.best = 0.0

    def push(self, adjusted: float) -> None:
        """Add one race's adjusted WPM, retiring the oldest once the window is full."""
        self.ring.append(adjusted)
        self.total += adjusted

        if len(self.ring) > WINDOW:
            self.total -= self.ring.pop(0)

        if len(self.ring) == WINDOW:
            self.best = max(self.best, self.total / WINDOW)


class SkillMedian:
    """The median best_wpm / predictedWpm ratio across a user's ranked English quotes."""

    def __init__(self) -> None:
        """Start with no quotes."""
        self.ratios: dict[str, float] = {}
        self.sorted: list[float] = []

    def update(self, quote_id: str, ratio: float) -> bool:
        """Record a quote's ratio, keeping the higher one. Returns whether it beat the old one."""
        previous = self.ratios.get(quote_id)
        if previous is not None:
            if ratio <= previous:
                return False
            self.sorted.pop(bisect.bisect_left(self.sorted, previous))

        self.ratios[quote_id] = ratio
        bisect.insort(self.sorted, ratio)

        return True

    @property
    def quotes(self) -> int:
        """Return how many distinct quotes back the median."""
        return len(self.sorted)

    @property
    def value(self) -> float:
        """Return the median ratio."""
        return median(self.sorted)


class NwpmState:
    """A user's running nWPM across both legs, gated on calibration."""

    def __init__(self) -> None:
        """Start an uncalibrated user with no races."""
        self.window = QPWindow()
        self.skill = SkillMedian()

    @property
    def calibrated(self) -> bool:
        """Return whether the user has enough ranked quotes for nWPM to show."""
        return self.skill.quotes >= CALIBRATION_MIN_QUOTES

    def recompute(self) -> float:
        """Return the current nWPM, or 0 while the user is uncalibrated."""
        if not self.calibrated:
            return 0.0

        return round(max(self.window.best, NWPM_BRIDGE_A + NWPM_BRIDGE_B * self.skill.value), 2)
