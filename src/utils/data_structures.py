"""Container types the standard library does not provide."""

from collections import Counter


class ScaledCounter(Counter):
    """A Counter whose values scale by a number."""

    def __mul__(self, factor) -> "ScaledCounter":
        """Return a new counter with every value multiplied by factor."""
        if not isinstance(factor, (int, float)):
            return NotImplemented

        if factor == 1:
            return self

        return ScaledCounter({key: value * factor for key, value in self.items()})

    __rmul__ = __mul__
