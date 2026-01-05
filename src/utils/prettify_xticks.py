from bisect import bisect_left


def prettyfyLengthXticks(xticks):
    rounding_thresholds = {0: 50, 100: 100, 250: 250, 2000: 1000, 5000: 2500, 20000: 10000}

    return prettyfyXticks(xticks, rounding_thresholds)


def prettyfyXticks(xticks, rounding_thresholds):
    limits = list(rounding_thresholds.keys())
    updated_xticks = []

    for xtick in xticks:
        i = bisect_left(limits, xtick)

        if i < len(limits):
            rounding_threshold = rounding_thresholds[limits[i - 1 if i >= 1 else i]]
        else:
            rounding_threshold = rounding_thresholds[limits[-1]]

        xtick = ((lower_value := xtick // rounding_threshold) + (lower_value == 0)) * rounding_threshold
        updated_xticks.append(xtick)
        
    return updated_xticks

