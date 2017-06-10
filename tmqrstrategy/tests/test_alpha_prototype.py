from tmqrfeed.manager import DataManager
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from tmqrfeed.costs import Costs
from datetime import datetime
import pandas as pd
from tmqrstrategy import StrategyBase


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


class AlphaGeneric(StrategyBase):
    def __init__(self, datamanager: DataManager, **kwargs):
        super().__init__(datamanager, **kwargs)

        self.temp = datetime.now()  # type: pd.DataFrame

    def setup(self):
        self.dm.series_primary_set(QuoteContFut, 'US.ES',
                                   timeframe='D')
        self.dm.costs_set('US', Costs())

    def calculate(self, *args):
        direction = 1
        period_slow, period_fast = args

        # Defining EXO price
        px = self.dm.quotes()['c']

        #
        #
        # Indicator calculation
        #
        #
        slow_ma = px.rolling(period_slow).mean()
        fast_ma = px.rolling(period_fast).mean()

        # Enry/exit rules
        entry_rule = CrossDown(fast_ma, slow_ma)
        exit_rule = (CrossUp(fast_ma, slow_ma))

        return self.exposure(entry_rule, exit_rule, direction)

    def calculate_position(self, date, exposure_record):
        # self.position.
        pass


if __name__ == '__main__':
    dm = DataManager()

    alpha = AlphaGeneric(dm)
    fut, opt = dm.chains_options_get('US.ES', datetime.now())
