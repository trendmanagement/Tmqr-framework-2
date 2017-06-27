from tmqrindex.index_base import IndexBase, INSTRUMENT_NA
from tmqr.errors import ArgumentError
from tmqrfeed.quotes.quote_contfut import QuoteContFut


class IndexContFut(IndexBase):
    _description_short = "EOD continuous futures series produced by QuoteContFut algorithm"
    _description_long = "EOD continuous futures series produced by QuoteContFut algorithm. " \
                        "Quotes and positions are included"

    _index_name = "ContFutEOD"

    def __init__(self, datamanager, **kwargs):
        super().__init__(datamanager, **kwargs)

        if self.instrument == INSTRUMENT_NA:
            raise ArgumentError("You must define 'instrument' in **kwargs")

    def setup(self):
        # Load instrument session from the DB
        if self.session is None:
            self.session = self.dm.session_set(self.instrument)
        else:
            self.dm.session_set(session_instance=self.session)

        self.dm.series_primary_set(QuoteContFut, self.instrument,
                                   timeframe='D', decision_time_shift=self.decision_time_shift)

    def set_data_and_position(self):
        """
        Setting continuous futures series and positions directly
        :return: 
        """
        self.data = self.dm.quotes()
        self.position = self.dm.position()
