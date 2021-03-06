import pandas as pd
from bdateutil import relativedelta
from tmqr.logs import log
from tmqrindex.index_exo_base import IndexEXOBase


# from datetime import datetime

# fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=self.opt_codes)

class EXO_Long_Yield_enhancement_active(IndexEXOBase):
    _description_short = "EXO_Long_Yield_enhancement_active"
    _description_long = ""

    _index_name = "EXO_Long_Yield_enhancement_active"

    def calc_exo_logic(self):
        """
        Calculates SmartEXO logic.
        NOTE: this method must use self.dm.quotes() or self.dm.quotes(series_key='for_secondary_series') to 
              calculate SmartEXO logic
        :return: Pandas.DataFrame with index like in dm.quotes() (i.e. primary quotes)
        """

        # Get primary instrument quotes (typically continuous futures quotes)
        pass

    def manage_position(self, dt, pos, logic_df):
        """
        Manages opened position (rollover checks/closing, delta hedging, etc)
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """
        #
        # Check expiration moment
        #
        if pos.almost_expired_ratio(dt) > 0:
            pos.close(dt)

        #
        # Check business days after last transaction
        #
        #pos_last_transaction_date = pos.last_transaction_date(dt)
        # log.debug("Last transaction date: {0}".format(pos_last_transaction_date))
        #days_after_last_trans = relativedelta(dt, pos_last_transaction_date).bdays

    def construct_position(self, dt, pos, logic_df):
        """
        EXO position construction method

        NOTE!: this method only called when there is no active position for 'dt'
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """

        try:
            opt_codes_in = self.context['opt_codes']
        except:
            opt_codes_in = []

        fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=opt_codes_in)

        # pos.add_transaction(dt, opt_chain.find(dt, 0.55, 'C', how='delta'), -1.0)
        # pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'P', how='delta'), -1.0)

        pos.add_transaction(dt, opt_chain.find(dt, 0.55, 'C', how='delta', opt_offset=1), -1.0)
        pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'P', how='delta', opt_offset=0), -1.0)