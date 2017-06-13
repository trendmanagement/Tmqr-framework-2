from tmqrfeed.manager import DataManager
from tmqrfeed.quotes import QuoteContFut
from tmqrfeed.quotes import QuoteIndex
from tmqrfeed.costs import Costs
from datetime import datetime
import pandas as pd
from tmqrstrategy import StrategyBase
from tmqrstrategy.optimizers import OptimizerBase, OptimizerGenetic


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
        # Load pre-saved EXO index ES ContFut instead of rebuild each time
        self.dm.series_primary_set(QuoteIndex, 'US.ES_ContFutEOD')

        self.dm.series_extra_set('fut', QuoteContFut, 'US.ES',
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

    def calculate_position(self, date: datetime, exposure_record: pd.DataFrame):
        primary_quotes_position = self.dm.position()

        # get net exposure for all members
        exposure = exposure_record['exposure'].sum()

        # Just replicate primary quotes position
        self.position.add_net_position(date, primary_quotes_position.get_net_position(date), qty=exposure)


if __name__ == '__main__':
    dm = DataManager()

    ALPHA_CONTEXT = {
        'wfo_params': {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 12,
        # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        },
        'optimizer_class': OptimizerBase,
        'optimizer_class_kwargs': {
            'nbest_count': 3,
            'nbest_fitness_method': 'max'
        },
        'opt_params': [
            ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
            ('period_fast', [1, 3, 10, 15, 20, 30])
        ],
        'members_count': 1,
        'costs_per_contract': 0.0,
        'scoring_type': 'netprofit'
    }

    alpha = AlphaGeneric(dm, **ALPHA_CONTEXT)

    alpha.run()

    equity = alpha.position.get_pnl_series()

    alpha.position
