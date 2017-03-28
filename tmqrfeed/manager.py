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
        self.feed = DataFeed(**kwargs)
        self.primary_quote = None
        """Quote* class instance for managing primary quote data"""

    def get_primary_data(self, quote_engine_cls, *args, **kwargs):
        """
        Fetch main ohlcv series used for algorithm and strategy calculations
        :param quote_engine_cls: Quote* class
        :return: dataframe for primary data
        """
        pass

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
