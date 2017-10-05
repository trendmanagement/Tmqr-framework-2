from tmqrindex.index_exo_base import IndexEXOBase


class EXOLongCall(IndexEXOBase):
    _description_short = "Long call EXO"
    _description_long = ""

    _index_name = "EXOLongCall"

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
        if pos.almost_expired_ratio(dt) == 1:
            pos.close(dt)

    def construct_position(self, dt, pos, logic_df):
        """
        EXO position construction method
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """
        # fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=['EW', ''])
        fut, opt_chain = self.dm.chains_options_get(self.instrument, dt, opt_codes=self.context['opt_codes'])

        pos.add_transaction(dt, opt_chain.find(dt, -15, 'P'), -1.0)
        pos.add_transaction(dt, opt_chain.find(dt, 15, 'C'), 1.0)
