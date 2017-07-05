from tmqrindex.index_base import IndexBase
from tmqrfeed.quotes.quote_base import QuoteBase
from tmqr.errors import SettingsError


class QuoteIndex(QuoteBase):
    """
    Quote algorithm for fetching pre-save index data from the DB
    """

    def __init__(self, index_name, **kwargs):
        """
        Init Quote Index quotes series
        :param index_name: full qualified index name as it stored in the DB
        :param kwargs:
            * 'set_session' - Use pre-saved index session settings to set datamanager's session (default: False)
            * 'check_session' - Compare actual datamanager's session with index session to prevent session errors (default: True)
        """
        super().__init__(**kwargs)
        self.index_name = index_name
        self.set_session = kwargs.get('set_session', False)
        self.check_session = kwargs.get('check_session', True)

    def __str__(self):
        return f"QuoteIndex-{self.index_name}"

    def build(self):
        """
        Loads index data from the DB and define Read-only position with decision_time_shift view

        :return: pd.DataFrame[QuotesSeries], QuotesPosition
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
