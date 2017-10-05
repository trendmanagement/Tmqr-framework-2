from bdateutil import relativedelta
from tmqr.logs import log
from tmqrindex.index_exo_base import IndexEXOBase


class EXOLongEnhance_DT_PutSpread(IndexEXOBase):
    _description_short = "EXO Vanilla DeltaTargeting LongEnhance PutSpread"
    _description_long = ""

    _index_name = "EXOLongEnhance_DT_PutSpread"

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
        #
        # Check expiration moment
        #
        if pos.almost_expired_ratio(dt) > 0:
            pos.close(dt)

        #
        # Check business days after last transaction
        #
        pos_last_transaction_date = pos.last_transaction_date(dt)
        # log.debug("Last transaction date: {0}".format(pos_last_transaction_date))
        days_after_last_trans = relativedelta(dt, pos_last_transaction_date).bdays

        if days_after_last_trans > 3:
            log.debug("Business days > 3, closing position")
            #    # Close the position
            pos.close(dt)
            #    # Avoid following checks
            return

            #
        # Delta based rebalance
        #
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

        fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=self.context['opt_codes'])

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
        # pos.add_transaction(dt, opt_chain.find(dt, 0.01, 'C', how='delta'), 2.0)
        # pos.add_transaction(dt, opt_chain.find(dt, 0.05, 'C', how='delta'), -3.0)
        # pos.add_transaction(dt, opt_chain.find(dt, 0.20, 'C', how='delta'), -1.0)
        # pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'P', how='delta'), 1.0)
        pos.add_transaction(dt, opt_chain.find(dt, 0.15, 'P', how='delta'), -2.0)
        pos.add_transaction(dt, opt_chain.find(dt, 0.05, 'P', how='delta'), 2.0)