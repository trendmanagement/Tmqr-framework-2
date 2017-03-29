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
        # Initiate low-level datafeed
        feed = kwargs.get('datafeed', None)
        if feed is None:
            datafeed_cls = kwargs.pop('datafeed_cls', DataFeed)
            feed = datafeed_cls(**kwargs, datamanager=self)

        self.datafeed = feed
        """DataFeed instance for low-level data fetching"""

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

    def series_get(self, asset, **kwargs):
        """
        Get asset's raw series from the DB
        :param asset: asset instance
        :param kwargs: DataFeed get_raw_series() **kwargs
        :return: series DataFrame
        """
        iinfo = asset.instrument_info
        kw_source_type = kwargs.get('source_type', asset.data_source)
        kw_timezone = kwargs.get('timezone', iinfo.timezone)
        kw_date_start = kwargs.get('date_start', asset.series_date_start)
        kw_date_end = kwargs.get('date_end', asset.series_date_end)

        return self.datafeed.get_raw_series(asset.ticker,
                                            source_type=kw_source_type,
                                            timezone=kw_timezone,
                                            date_start=kw_date_start,
                                            date_end=kw_date_end
                                            )

    def price_get(self, asset, date):
        """
        Get price at decision and execution time for given asset
        :param asset: Contract class instance
        :param date: 
        :return: 
        """
