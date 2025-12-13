from collections import Counter


class ScaledCounter(Counter):
    def __mul__(self, factor):
        if not isinstance(factor, (int, float)):
            return NotImplemented

        if factor == 1:
            return self

        return ScaledCounter({key: value * factor for key, value in self.items()})

    __rmul__ = __mul__
