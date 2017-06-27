from tmqrindex.index_base import IndexBase
from tmqrfeed.quotes.quote_base import QuoteBase
from tmqr.errors import SettingsError


class QuoteIndex(QuoteBase):
    """
    Quote algorithm for fetching pre-save index data from the DB
    """

    def __init__(self, index_name, **kwargs):
        super().__init__(**kwargs)
        self.index_name = index_name
        """Full qualified index name"""

        self.set_session = kwargs.get('set_session', False)
        """Use index session settings to set datamanager session"""

        self.check_session = kwargs.get('check_session', True)
        """Force session equality checks, make sure that datamanager's and index's sessions the same"""

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
        try:
            actual_session = self.dm.session_get()
        except SettingsError:
            actual_session = None

        if idx.session is None:
            raise SettingsError(f"Pre-saved index doesn't have 'session' records, check the database validity. "
                                f"Index: {self.index_name}")

        if actual_session is None:
            if self.set_session:
                self.dm.session_set(session_instance=idx.session)
        else:
            if self.check_session:
                # Make sure that all sessions for all indexes are equal

                if actual_session != idx.session:
                    raise SettingsError(
                        "The session rules must be equal for every index loaded and datamanager.session_set(...)  \n"
                        f"Actual session: \n{actual_session}\n",
                        f"{self.index_name} session:\ {idx.session}"
                    )

        return idx.data, idx.position
