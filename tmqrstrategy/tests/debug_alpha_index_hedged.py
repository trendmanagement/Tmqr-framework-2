from tmqrfeed.manager import DataManager
from tmqrstrategy.optimizers import OptimizerBase, OptimizerGenetic

from tmqrstrategy.tests.debug_alpha_prototype import AlphaGeneric

import pandas as pd
from tmqrfeed.quotes import QuoteIndex
from tmqr.logs import log
from tmqr.errors import *
from datetime import datetime


class Strategy_HedgedByIndex(AlphaGeneric):
    def setup(self):
        # Call parent Strategy_DSP_LPBP_Combination.setup() -> tmqrstrategy.strategy_alpha.StrategyAlpha.setup()
        super().setup()

        #
        # We have to add index we wanted to hedge by
        #
        HEDGE_IDX_NAME = self.context['index_hedge_name']
        self.dm.series_extra_set('index_hedge', QuoteIndex, HEDGE_IDX_NAME, set_session=True, check_session=True)

    #
    # This is exact copy/paste of souce code of tmqrstrategy.strategy_alpha.StrategyAlpha.calculate_position() method
    #
    def calculate_position(self, date: datetime, exposure_record: pd.DataFrame):
        """
        This alpha just replicates EXO/SmartEXO index position


        This method used for position construction based on exposure information returned from calculate(),
        here you can initiate (replicate) EXO index position or setup any custom position you want.
        """
        # Get the position of Quote algo (in this case current cont futures)
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
        self.position.add_net_position(date, replicated_pos, qty=exposure)

        #
        # Do new position management magic here
        #
        index_hedge_position = self.dm.position('index_hedge')
        try:
            hedge_position_rec = index_hedge_position.get_net_position(date)
            # Add index position as hedge
            # NOTE: exposure - is a alpha's exporure of trade, when alpha is out of market
            #                  exposure equals 0, this means that means no position and hedge
            # NOTE: self.context['index_hedge_direction'] allowed 1, -1, or even 0 - i.e. no hedge
            self.position.add_net_position(date, hedge_position_rec,
                                           qty=exposure * self.context['index_hedge_direction'])
        except PositionNotFoundError as exc:
            log.error(f"Couldn't find hedged index position! {exc}")

            # print(f'Exposure: {exposure}')
            # print(self.position)


if __name__ == '__main__':
    ALPHA_CONTEXT = {
        'name': 'DEBUG_ES_NewStrategy_DSP_LPBP_Combination_With_IndexHedge',
        # Global alpha name, which be used for load/save from DB
        'context': {  # Strategy specific settings
            # These settings only applycable for alphas derived from StrategyAlpha strategy
            # StrategyAlpha - is a classic EXO/SmartEXO based alpha
            'index_name': 'US.ES_ContFutEOD',  # Name of EXO index to trade

            # !!! NEW RECORD
            'index_hedge_name': 'US.ES_EXOSpreadFixed',  # Name of the index used for hedge
            'index_hedge_direction': 1,  # ALLOWED 1, -1, or even 0 - i.e. no hedge
            #

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

    # DataManager is a core class of the framework
    dm = DataManager()

    # Init alpha class and run
    alpha = Strategy_HedgedByIndex(dm, **ALPHA_CONTEXT)

    alpha.run()
