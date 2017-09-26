from tmqrfeed.manager import DataManager
from tmqrindex.index_exo_base import IndexEXOBase
from datetime import datetime

from bdateutil import relativedelta
from tmqr.logs import log


class ES_EXOWeeklyCalendarPutSpread(IndexEXOBase):
    _description_short = "Short front Puts long deeper"
    _description_long = ""

    _index_name = "EXOWeekly_Calendar_putspread"

    def calc_exo_logic(self):
        """
        Calculates SmartEXO logic.
        NOTE: this method must use self.dm.quotes() or self.dm.quotes(series_key='for_secondary_series') to 
              calculate SmartEXO logic
        :return: Pandas.DataFrame with index like in dm.quotes() (i.e. primary quotes)
        """
        pass

    def manage_position(self, dt, pos, logic_df):
        """
        Manages opened position (rollover checks/closing, delta hedging, etc)
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """
        if pos.almost_expired_ratio(dt) > 0:
            pos.close(dt)

    def construct_position(self, dt, pos, logic_df):
        """
        EXO position construction method
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """
        # fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=['E1C','E2C','E3C','E4C'])
        # fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW1','EW4'])
        # fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW',''])
        # Selling ATM call
        fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW2'])
        pos.add_transaction(dt, opt_chain.find(dt, 0.2, 'P', how='delta'), 1.0)

        # Hedging with next series by delta 0.75 call
        fut_next, opt_chain_next = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW1'])
        pos.add_transaction(dt, opt_chain_next.find(dt, 0.4, 'P', how='delta'), -3.0)

        fut_next, opt_chain_next = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW4'])
        pos.add_transaction(dt, opt_chain_next.find(dt, 0.15, 'P', how='delta'), 2.0)