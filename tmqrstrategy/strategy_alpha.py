from tmqrstrategy.strategy_base import StrategyBase
from tmqr.errors import StrategyError, NotFoundError
from tmqrfeed.quotes import QuoteIndex
from tmqrfeed.costs import Costs
import pandas as pd
import numpy as np
from datetime import datetime


class StrategyAlpha(StrategyBase):
    """
    Single instrument strategy with custom stats
    """

    def setup(self):
        if 'index_name' not in self.context:
            raise StrategyError("You must set 'index_name' in 'context' kwarg")
        if 'costs_per_option' not in self.context:
            raise StrategyError("You must set 'costs_per_option' in 'context' kwarg")
        if 'costs_per_contract' not in self.context:
            raise StrategyError("You must set 'costs_per_contract' in 'context' kwarg")

        #
        # Fetching index and setting the session based on index's settings rules
        # Look for kwargs help in tmqrfeed.quotes.quote_index.py source code
        self.dm.series_primary_set(QuoteIndex, self.context['index_name'], set_session=True, check_session=True)

        self.dm.costs_set('US', Costs(per_option=self.context['costs_per_option'],
                                      per_contract=self.context['costs_per_contract']))


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
            try:
                position_delta[i] = self.position.delta(dt)
            except NotFoundError:
                pass

        series['delta'] = position_delta

        return stats

    def calculate_position(self, date: datetime, exposure_record: pd.DataFrame):
        """
        This alpha just replicates EXO/SmartEXO index position


        This method used for position construction based on exposure information returned from calculate(),
        here you can initiate (replicate) EXO index position or setup any custom position you want.
        """
        # Get the position of Quote algorithm (in this case current cont futures)
        primary_quotes_position = self.dm.position()

        # ALSO you can get secondary positions
        # secondary_position = self.dm.position('CONTFUT')

        # get net exposure for all members
        # exposure_record - is a slice of exposures results of picked alphas at 'date'

        # We are calling sum() because we have multiple records of 'exposure'
        # 1-alpha member of best in the swarm per row
        if 'exposure' not in exposure_record:
            raise StrategyError(
                "'exposure_record' expected to have 'exposure' column, check alpha's calculate(...) method "
                "to make sure that it returns valid pandas.DataFrame with exposure column or just check "
                "for 'return self.exposure(...)' in the last line")
        exposure = exposure_record['exposure'].sum()

        #
        # Just replicate primary quotes position
        #
        replicated_pos = primary_quotes_position.get_net_position(date)
        self.position.set_net_position(date, replicated_pos, qty=exposure)
