from tmqrindex.index_base import IndexBase, INSTRUMENT_NA
from tmqr.errors import ArgumentError, ChainNotFoundError, QuoteNotFoundError
from tmqrfeed.quotes.quote_contfut import QuoteContFut
from tmqrfeed.costs import Costs
from tmqr.logs import log
from tmqrfeed.position import Position


class IndexEXOBase(IndexBase):
    _description_short = "EOD continuous futures series produced by QuoteContFut algorithm"
    _description_long = "EOD continuous futures series produced by QuoteContFut algorithm. " \
                        "Quotes and positions are included"

    _index_name = "EXOBase"

    def __init__(self, datamanager, **kwargs):
        super().__init__(datamanager, **kwargs)

        if self.instrument == INSTRUMENT_NA:
            raise ArgumentError("You must define 'instrument' in **kwargs")

        self.costs_futures = self.context.get('costs_futures', 0.0)
        self.costs_options = self.context.get('costs_options', 0.0)

    def setup(self):
        self.dm.series_primary_set(QuoteContFut, self.instrument,
                                   timeframe='D', decision_time_shift=self.decision_time_shift)
        self.dm.costs_set(self.instrument.split('.')[0], Costs(per_contract=self.costs_futures,
                                                               per_option=self.costs_options))

    def set_data_and_position(self):
        """
        Setting continuous futures series and positions directly
        :return: 
        """

        pos = Position(self.dm, decision_time_shift=self.decision_time_shift)

        exo_df = self.calc_exo_logic()

        for dt in self.dm.quotes().index:

            try:
                pos.keep_previous_position(dt)

                # Getting SmartEXO logic data point for current date
                logic_df = None
                if exo_df:
                    try:
                        logic_df = exo_df[dt]
                    except KeyError:
                        pass

                self.manage_position(dt, pos, logic_df)

                if not pos.has_position(dt):
                    log.debug('Opening new position')
                    log.debug(f"Date: {dt}")
                    self.construct_position(dt, pos, logic_df)
                    log.debug(f'Position\n {repr(pos)}')
            except ChainNotFoundError:
                log.error(f"ChainNotFoundError: {dt}")
            except QuoteNotFoundError:
                log.error(f"QuoteNotFoundError: {dt}")

        self.data = pos.get_pnl_series()
        self.position = pos

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
        pass

    def construct_position(self, dt, pos, logic_df):
        """
        EXO position construction method
        :param dt: current datetime
        :param pos: Position instance
        :param logic_df: result of calc_exo_logic()[dt]  if applicable
        :return: nothing, manages 'pos' in place
        """
        pass

    @property
    def index_name(self):
        return f"{self.instrument}_{self._index_name}"
