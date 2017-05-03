from tmqrindex.index_base import IndexBase
from tmqrfeed.quotes.quote_base import QuoteBase


class QuoteIndex(QuoteBase):
    """
    Quote algorithm for fetching pre-save index data from the DB
    """

    def __init__(self, index_name, **kwargs):
        super().__init__(**kwargs)
        self.index_name = index_name

    def __str__(self):
        return f"QuoteIndex-{self.index_name}"

    def build(self):
        """
        Loads index data from the DB and define Read-only position with decision_time_shift view
        :return: 
        """
        idx = IndexBase.deserialize(self.dm,
                                    self.dm.datafeed.data_engine.db_load_index(self.index_name),
                                    as_readonly=True
                                    )
        return idx.data, idx.position
