from tmqr.errors import *
from tmqrfeed.datafeed import DataFeed


class DataManager:
    """
    Utility class used for data management of the strategy. 
    Also this class will be used for following purposes:
    * Quotes building - acts as a container for a different quotes types produced by Quote* classes.
    * Quotes aligning - if several quotes sources utilized with different timestamps layout
    * Return positions structure - contracts names and information for each date of the dataseries
    * Quotes sanity checks - warns if one of the series are delayed or has data holes
    * Data access interface and container - stores all data requested by strategies/contracts and provides interface for data management
    * Smart chains fetching - selects actual options and futures chains by several criterias
    * Quotes caching - reduces DB calls and speedup data access if this data is already fetched 
    * Extradata fetching - fetch extradata (like indexes or non-price data) from the DB and properly align this data    
    """

    def __init__(self, **kwargs):
        """
        Init DataManager class
        :param kwargs: 
        """
        datafeed_cls = kwargs.get('datafeed_cls', DataFeed)
        self.feed = datafeed_cls(**kwargs)

        # Quotes dataframe for primary series
        self._primary_quotes = None
        # Secondary dataframes dictionary for secondary series quotes
        self._secondary_quotes = {}

        # Primary series positions
        self._primary_positions = None
        # Secondary series positions dictionary
        self._secondary_positions = {}

    def series_primary_set(self, quote_engine_cls, *args, **kwargs):
        """
        Fetch main series used for algorithm and strategy calculations
        :param quote_engine_cls: Quote* class
        :param args: positional arguments for given Quote* class
        :param kwargs: kwargs for given Quote* class
        :return: None
        """
        if self._primary_quotes is not None:
            raise DataManagerError("series_primary_set() already called, only one instance of primary quotes allowed")

        quote_engine = quote_engine_cls(*args, **kwargs)
        self._primary_quotes, self._primary_positions = quote_engine.build()

        # Checking series validity
        self.series_check(self._primary_quotes)

    def series_extra_set(self, name, quote_engine_cls, *args, **kwargs):
        """
        Fetch additional series, align them to primary series and save by 'name'
        :param name: Extra series name for further access
        :param quote_engine_cls: Quote* class
        :param args: positional arguments for given Quote* class
        :param kwargs: kwargs for given Quote* class
        :return: None 
        """
        if self._primary_quotes is None:
            # Make sure that primary quotes are filled before
            raise DataManagerError("Call series_primary_set() before series_extra_set()")

        if name in self._secondary_quotes or name in self._secondary_positions:
            # Check for 'name' duplicate for extra series
            raise DataManagerError(f"You have already added extra series with name '{name}'")

        quote_engine = quote_engine_cls(*args, **kwargs)
        quotes, pos = quote_engine.build()

        # Checking quotes validity
        self.series_check(quotes)

        # Align and store extra series
        self._secondary_quotes[name] = self.series_align(self._primary_quotes, quotes)
        self._secondary_positions[name] = pos

    def series_align(self, primary_quotes, extra_quotes):
        # TODO: implement series alignment
        return extra_quotes

    def series_check(self, quotes):
        # TODO: implement series checks
        return True



    def get_extra_data(self, quote_engine, data_name):
        """
        Fetch secondary data which could be used as additional information for decision making process of the algorithm
        :param quote_engine: Quote* class instance
        :param data_name: key for accessing primary data
        :return: extradata class instance
        """
        pass

    def __getitem__(self, item):
        """
        Fetch secondary data by name (data_name parameter in get_extra_data request)
        :param item: data_name parameter in get_extra_data request
        :return: extradata class instance
        """
        pass
