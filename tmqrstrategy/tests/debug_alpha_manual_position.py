from tmqrfeed.manager import DataManager
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from tmqrfeed.costs import Costs
from datetime import datetime
import pandas as pd
from tmqrstrategy import StrategyBase, StrategyAlpha
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


class AlphaGenericManual(StrategyAlpha):
    def __init__(self, datamanager: DataManager, **kwargs):
        super().__init__(datamanager, **kwargs)

        self.temp = datetime.now()  # type: pd.DataFrame

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
        exposure = exposure_record['exposure'].sum()

        #
        # Keep previous position
        #     Otherwise you have to construct position from scratch at the beginning of each day
        self.position.keep_previous_position(date)

        # You MUST also manage expired position
        if self.position.almost_expired_ratio(date) > 0:
            self.position.close(date)

        if not self.position.has_position(date):
            if exposure != 0:
                # Getting instrument name from index name
                # 'US.ES_ContFutEOD' -> 'US.ES'
                instrument_name = self.context['index_name'].split('_')[0]

                fut, opt_chain = self.dm.chains_options_get(instrument_name, date)

                # set the primary position
                self.position.add_transaction(date, fut, exposure)

                if exposure > 0:
                    # Hedgind long alphas exposures by long put
                    self.position.add_transaction(date, opt_chain.find(date, 0.35, 'P', how='delta'), 1.0 * exposure)
                elif exposure < 0:
                    # Hedgind short alphas exposures by long put
                    self.position.add_transaction(date, opt_chain.find(date, 0.35, 'C', how='delta'), 1.0 * exposure)
        else:
            if exposure == 0:
                # Close all
                self.position.close(date)


if __name__ == '__main__':
    dm = DataManager()

    ALPHA_CONTEXT = {
        'name': 'DEBUG_ALPHA_PROTOTYPE',
        'context': {  # Strategy specific settings
            # These settings only applycable for alphas derived from StrategyAlpha strategy
            # StrategyAlpha - is a classic EXO/SmartEXO based alpha
            'index_name': 'US.ES_ContFutEOD',  # Name of EXO index to trade
            'costs_per_option': 3.0,
            'costs_per_contract': 3.0,
        },
        'wfo_params': {
            'window_type': 'rolling',  # Rolling window for IIS values: rolling or expanding
            'period': 'M',  # Period of rolling window 'M' - monthly or 'W' - weekly
            'oos_periods': 2,  # Number of months is OOS period
            'iis_periods': 12,
            # Number of months in IIS rolling window (only applicable for 'window_type' == 'rolling')
        },
        'wfo_optimizer_class': OptimizerBase,
        'wfo_optimizer_class_kwargs': {
            'nbest_count': 3,
            'nbest_fitness_method': 'max'
        },
        'wfo_opt_params': [
            ('period_slow', [10, 30, 40, 50, 70, 90, 110]),
            ('period_fast', [1, 3, 10, 15, 20, 30])
        ],
        'wfo_members_count': 1,
        'wfo_costs_per_contract': 0.0,
        'wfo_scoring_type': 'netprofit'
    }

    alpha = AlphaGenericManual(dm, **ALPHA_CONTEXT)

    alpha.run()

    equity = alpha.position.get_pnl_series()

    stats = alpha.stats

    pass
