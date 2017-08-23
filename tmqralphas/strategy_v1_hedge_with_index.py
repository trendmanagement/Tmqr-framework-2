from tmqrfeed.quotes.quote_contfut import QuoteContFut
from tmqrfeed.costs import Costs
from datetime import datetime
import pandas as pd
from tmqrstrategy import StrategyBase
from tmqrfeed.quotes import QuoteIndex
from tmqr.errors import PositionNotFoundError
from tmqrfeed import DataManager
from tmqr.logs import log

#
# Using some of V1 libs
#
from exobuilder.data.exostorage import EXOStorage
from scripts.settings import *


class AlphaV1HedgeWithIndex(StrategyBase):
    def __init__(self, datamanager: DataManager, **kwargs):
        super().__init__(datamanager, **kwargs)

    def setup(self):

        self.dm.session_set(self.context['instrument'])

        self.dm.series_primary_set(QuoteContFut, self.context['instrument'],
                                   timeframe='D')

        HEDGE_IDX_NAME = self.context['index_hedge_name']
        self.dm.series_extra_set('index_hedge', QuoteIndex, HEDGE_IDX_NAME, set_session=True, check_session=True)

        self.dm.costs_set('US', Costs())

        # Getting Framework v1 alpha data
        storage = EXOStorage(MONGO_CONNSTR, MONGO_EXO_DB)
        swarms = storage.swarms_data(self.context['v1_alphas'])
        self.v1_exposure = pd.DataFrame({k: v['swarm_series']['exposure'] for k, v in swarms.items()})
        self.v1_equity = pd.DataFrame({k: v['swarm_series']['equity'] for k, v in swarms.items()})

        px_index = self.dm.quotes().index
        self.v1_exposure.index = self.v1_exposure.index.tz_localize(px_index.tz)
        self.v1_exposure = self.v1_exposure.reindex(px_index, method='ffill')

        self.v1_equity.index = self.v1_equity.index.tz_localize(px_index.tz)
        self.v1_equity = self.v1_equity.reindex(px_index, method='ffill')

    def calculate(self, *args):
        direction, = args

        # Defining EXO price
        px = self.dm.quotes()['c']

        #
        # Calculating exposure of V1 alphas
        #
        exposure = self.v1_exposure.sum(axis=1)
        exposure = exposure.reindex(px.index, method='ffill')

        self.v1_alpha_exposure = exposure

        return pd.DataFrame({'exposure': exposure})

    def calculate_position(self, date: datetime, exposure_record: pd.DataFrame):
        primary_quotes_position = self.dm.position()

        # get net exposure for all members
        exposure = exposure_record['exposure'].sum()

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
                                           qty=abs(exposure) * self.context['index_hedge_direction'])
        except PositionNotFoundError as exc:
            log.error(f"Couldn't find hedged index position! {exc}")
