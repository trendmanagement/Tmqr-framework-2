import pandas as pd
from bdateutil import relativedelta
from tmqr.logs import log
from tmqrindex.index_exo_base import IndexEXOBase


# from datetime import datetime

# fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=self.opt_codes)

from scipy import signal
import numpy as np


def lp_filter(series, filt_order, filt_freq):
    series = series.copy()
    b, a = signal.butter(filt_order, filt_freq, btype='lowpass')

    series.loc[:] = signal.lfilter(b, a, series)

    return series

class EXOSemiFuture_DynKel_80_20_shorts_lp(IndexEXOBase):
    _description_short = "EXO Vanilla DeltaTargeting DynKel Delta Risk Reversal"
    _description_long = ""

    _index_name = "EXO_SemiFuture_DynKel_80_20_shorts_LP"

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
        #typical_px = (ohlc.h + ohlc.l + ohlc.c) / 3.0
        #typical_avg = typical_px.rolling(10).mean()

        #keltner_direction = typical_avg > typical_avg.shift()

        ma_periods = 10
        periods_to_alpha = 2 / (ma_periods + 1)

        typical_px = (ohlc.h + ohlc.l + ohlc.c) / 3.0
        typical_avg = lp_filter(typical_px, 1, periods_to_alpha)


        lp_freqs = np.arange(periods_to_alpha/4, periods_to_alpha*2, periods_to_alpha/4)
        lp_df = pd.DataFrame(index=typical_avg.index)

        for f in lp_freqs:
            lp_df['lp_freq{:0.2f}'.format(f)] = lp_filter(typical_avg, 1, f)

        consensus = (lp_df >= lp_df.shift(1)).mean(1)

        lags = 5
        for i in range(1, lags):
            consensus += (lp_df >= lp_df.shift(i)).mean(1)

        consensus /= lags

        keltner_direction = consensus > consensus.shift()

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
        #log.debug("Last transaction date: {0}".format(pos_last_transaction_date))
        days_after_last_trans = relativedelta(dt, pos_last_transaction_date).bdays

        if days_after_last_trans > 3:
             log.debug("Business days > 3, closing position")
        #    # Close the position
             pos.close(dt)
        #    # Avoid following checks
             return


        #
        # Delta based rebalance
#         #
        delta = pos.delta(dt)
        if delta > 0.55:
            log.debug("Delta > 0.35")
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

        #
        # Help
        #
        """
        Find option contract in chain using 'how' criteria
        :param dt: analysis date
        :param item: search value
        :param opttype: option type 'C' or 'P'
        :param how: search method
                    - 'offset' - by strike offset from ATM
                    - 'strike' - by strike absolute value
                    - 'delta'  - by delta
                        Search option contract by delta value:
                        If delta ==  0.5 - returns ATM call/put
                        If delta > 0.5 - returns ITM call/put near target delta
                        If delta < 0.5 - returns OTM call/put near target delta
        :param kwargs:
            * how == 'offset' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5)
            * how == 'delta' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5)
                - strike_limit - how many strikes to analyse from ATM (default: 30)
        :return: OptionContract
        Example:
        pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'C', how='delta'), 1.0)

        pos.add_transaction(dt, # Current date
                            opt_chain.find( # Find option in chain by delta
                                            dt,   # Current date     
                                            0.15, # Delta value (because how='delta'), otherwise ATM offset
                                            'C',  # Search for call
                                            how='delta'), # Search by delta                            
                            1.0 # Transaction Qty
                            )

        """
        if logic_df['keltner_direction_current'] == True:
            # Open the position when keltner channel is up
            pos.add_transaction(dt, opt_chain.find(dt, 0.30, 'P', how='delta'), -1.0)
            pos.add_transaction(dt, opt_chain.find(dt, 0.50, 'C', how='delta'), 1.0)
        else:

            # Open the position when keltner channel is down
            pos.add_transaction(dt, opt_chain.find(dt, 0.05, 'P', how='delta'), -1.0)
            pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'C', how='delta'), 1.0)