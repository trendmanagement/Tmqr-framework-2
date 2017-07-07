"""
TODO: brief description of module
"""

import pandas as pd
import numpy as np


def CrossUp(a, b):
    """
    A crosses up B
    """
    return (a.shift(1) < b.shift(1)) & (a > b)


def CrossDown(a, b):
    """
    A crosses down B
    """
    return (a.shift(1) > b.shift(1)) & (a < b)


def ATR(H, L, C, period):
    """
    Wilders ATR
    :param H: high price
    :param L: low price
    :param C: close price
    :param period:
    :return: AverageTrueRange of OHLC
    """
    barcount = len(C)
    result = pd.Series(index=C.index)
    sumtr = 0.0
    avg = 0.0

    for i in range(barcount):
        if i == 0:
            sumtr = H.values[i] - L.values[i]
        else:
            v = max(H.values[i] - L.values[i],
                    max(abs(H.values[i] - C.values[i - 1]), abs(L[i] - C[i - 1]))
                    )
            if i <= period - 1:
                # Skipping points < period
                sumtr += v

                # First point is a simple average
                if i == period - 1:
                    avg = sumtr / period
            else:
                # Wilders smoothing
                avg = ((1.0 / period) * v + (1.0 - 1.0 / period) * avg)
                result[i] = avg
    return result
