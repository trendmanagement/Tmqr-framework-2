from tmqrstrategy.strategy_base import StrategyBase
from tmqr.errors import StrategyError
import pandas as pd
import numpy as np


class StrategyAlpha(StrategyBase):
    """
    Single instrument strategy with custom stats
    """

    def process_stats(self):
        """
        Calculate alpha strategy statistics
        :return: stats dictionary
        """
        stats = super().process_stats()

        series = stats['series']
        position_delta = np.zeros(len(series))

        for i, dt in enumerate(series.index):
            # Calculate position delta
            position_delta[i] = self.position.delta(dt)

        series['delta'] = position_delta

        return stats
