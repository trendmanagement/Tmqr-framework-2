import pandas as pd
from bdateutil import relativedelta
from tmqr.logs import log
from tmqrindex.index_exo_base import IndexEXOBase


# from datetime import datetime

# fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=self.opt_codes)

class EXO_RiskReversal_Passive_Puts_For_Longs(IndexEXOBase):
    _description_short = "EXO_RiskReversal_Passive_Puts_For_Longs"
    _description_long = ""

    _index_name = "EXO_RiskReversal_Passive_Puts_For_Longs"

    def calc_exo_logic(self):
        """
        Calculates SmartEXO logic.
        NOTE: this method must use self.dm.quotes() or self.dm.quotes(series_key='for_secondary_series') to 
              calculate SmartEXO logic
        :return: Pandas.DataFrame with index like in dm.quotes() (i.e. primary quotes)
        """

        # Get primary instrument quotes (typically continuous futures quotes)
        ohlc = self.dm.quotes()

        # https://en.wikipedia.org/wiki/Keltner_channel
        typical_px = (ohlc.h + ohlc.l + ohlc.c) / 3.0
        typical_avg = typical_px.rolling(90).mean()

        keltner_direction = typical_avg > typical_avg.shift()

        return pd.DataFrame({'keltner_direction_current': keltner_direction,
                             'keltner_direction_prev': keltner_direction.shift(),
                             })

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
        # Smart EXO Keltner channel logic
        #
        if logic_df['keltner_direction_current'] != logic_df['keltner_direction_prev']:
            log.debug(f"Keltner channel direction changed")
            # Close the position
            pos.close(dt)

        #
        # Check business days after last transaction
        #
        pos_last_transaction_date = pos.last_transaction_date(dt)
        # log.debug("Last transaction date: {0}".format(pos_last_transaction_date))
        days_after_last_trans = relativedelta(dt, pos_last_transaction_date).bdays

        if days_after_last_trans > 20:
            log.debug("Business days > 3, closing position")
            #    # Close the position
            pos.close(dt)
            #    # Avoid following checks
            return

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

        if logic_df['keltner_direction_current'] == True:
            pos.add_transaction(dt, opt_chain.find(dt, 0.05, 'P', how='delta'), 1.0)
        else:
            pos.add_transaction(dt, opt_chain.find(dt, 0.50, 'P', how='delta'), 1.0)