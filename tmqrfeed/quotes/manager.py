class QuoteManager:
    """
    Utility class used for quotes management of the strategy, acts as a container for a different quotes types produced
    by Quote* classes. Also this class could be used for following purposes:
    * Quotes aligning - is several quotes sources utilized
    * Return positions structure - contracts names and information for each date of the dataseries
    * Quotes sanity checks - warns if one of the series are delayed or has data holes
    * Data access interface and container - stores all data requested by algorithm and provides interface for data management
    """

    def get_primary_data(self, quote_engine):
        """
        Fetch main ohlcv series used for algorithm and strategy calculations
        :param quote_engine: Quote* class instance
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
