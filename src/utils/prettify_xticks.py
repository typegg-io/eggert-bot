from bisect import bisect_left

from numpy import ndarray, array, power, log as np_log


# The min overlapping scale is a float between 0 and 1 of the minimum allowable width between two xtics normalised over the total width of the minimum and the maximum xtick
def prettyfyLogLengthXticks(xticks, log_base, min_overlapping_scale: float=0.068) -> ndarray:
    rounding_thresholds = {0: 50, 100: 100, 250: 250, 2000: 1000, 5000: 2500, 20000: 10000}

    xticks = power(log_base, xticks)
    xticks = prettyfyXticks(xticks, rounding_thresholds)
    xticks = np_log(xticks) / np_log(log_base)
    xticks = removeOverlappingXticks(xticks, min_overlapping_scale)
    
    return xticks


def prettyfyLengthXticks(xticks, min_overlapping_scale: float=0.068) -> ndarray:
    rounding_thresholds = {0: 50, 100: 100, 250: 250, 2000: 1000, 5000: 2500, 20000: 10000}

    return removeOverlappingXticks(prettyfyXticks(xticks, rounding_thresholds), min_overlapping_scale)
    

def prettyfyXticks(xticks, rounding_thresholds) -> ndarray:
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
    
    return array(updated_xticks)


def removeOverlappingXticks(xticks, min_overlapping_scale: float) -> ndarray:
    xticks = sorted(xticks)

    if len(xticks) >= 2:
        new_xticks = [xticks[0]]
        xtick_scale = xticks[-1] - xticks[0]

        for i in range(1, len(xticks)):
            xtick = xticks[i]

            # Checks if the current and the previous xtick overlap, in case they don't add the current xtick to the new xtick list
            if (xtick - new_xticks[-1]) / xtick_scale >= min_overlapping_scale:
                new_xticks.append(xtick)

        # Add last xtick to the array and remove the second to last open
        # Either this is the same value twice, so it cancels out or it's an old value that overlaps, and thus the overlapping value gets removed
        new_xticks.append(xticks[-1])
        new_xticks.pop(-2)

        return array(new_xticks)

    return array(xticks)
