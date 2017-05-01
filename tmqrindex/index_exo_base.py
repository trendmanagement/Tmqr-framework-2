from tmqrindex.index_base import IndexBase, INSTRUMENT_NA
from tmqr.errors import ArgumentError
from tmqrfeed.quotes.quote_contfut import QuoteContFut


class IndexEXOBase(IndexBase):
    _description_short = "EOD continuous futures series produced by QuoteContFut algorithm"
    _description_long = "EOD continuous futures series produced by QuoteContFut algorithm. " \
                        "Quotes and positions are included"

    _index_name = "EXOBase"

    def __init__(self, datamanager, **kwargs):
        super().__init__(datamanager, **kwargs)

        if self.instrument == INSTRUMENT_NA:
            raise ArgumentError("You must define 'instrument' in **kwargs")

    def setup(self):
        self.dm.series_primary_set(QuoteContFut, self.instrument,
                                   timeframe='D', decision_time_shift=self.decision_time_shift)

    def set_data_and_position(self):
        """
        Setting continuous futures series and positions directly
        :return: 
        """
        self.data = self.dm.quotes()
        self.position = self.dm.position()

    @property
    def index_name(self):
        return f"{self.instrument}_{self._index_name}"
