from tmqrfeed.manager import DataManager
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from tmqrfeed.costs import Costs
from datetime import datetime, timedelta
import pandas as pd
from tmqrstrategy import StrategyBase
from tmqrstrategy.optimizers import OptimizerBase, OptimizerGenetic
from tmqrstrategy.tests.debug_alpha_prototype import AlphaGeneric
from unittest.mock import patch

if __name__ == '__main__':
    dm = DataManager(date_end=datetime(2012, 6, 1))

    ALPHA_CONTEXT = {
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

    alpha = AlphaGeneric(dm, **ALPHA_CONTEXT)

    alpha.run()
    equity = alpha.position.get_pnl_series()
    pos = alpha.position

    print("!!!! Initial alpha calculation step")
    with patch('tmqrstrategy.strategy_base.StrategyBase.date_now') as mock_date_now:
        curr_date = datetime(2012, 2, 20)
        mock_date_now.return_value = curr_date.date()
        dm2 = DataManager(date_end=curr_date)
        # Do first run
        alpha_name = 'debug_alpha_online_recalc'
        alpha_online = AlphaGeneric(dm2, **ALPHA_CONTEXT, name=alpha_name)
        alpha_online.run()
        alpha_online.save()

        while curr_date <= datetime(2012, 6, 1):

            # Simulate every day recalculation
            print(f'==== Processing date: {curr_date}')
            # Pretending that current date is date.now()
            mock_date_now.return_value = curr_date.date()
            dm2 = DataManager(date_end=curr_date)

            # Load and run
            saved_alpha = AlphaGeneric.load(dm2, alpha_name)
            saved_alpha.run()
            saved_alpha.save()
            curr_date += timedelta(days=1)

    # Comparing alpha positions
    saved_alpha = AlphaGeneric.load(dm2, alpha_name)

    assert saved_alpha.position == alpha.position
