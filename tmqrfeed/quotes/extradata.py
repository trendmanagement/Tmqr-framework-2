class ExtraData:
    """
    Extradata series class used for fetching and managing extradata series stored in MongoDB
    Examples of extradata:
    * EXO pre-calculated prices
    * Algorithmically pre-calculated values based on OHLC of the raw data analysis
    * Non-price data for asset (fundamental data values, news calendar, COT, IV indexes etc.)
    """

    @property
    def instrument(self):
        """
        Underlying instrument for extradata.
        Could be non existing instrument if the extradata is globally related, like economic calendar events.
        :return:
        """
        pass

    @property
    def name(self):
        """
        Name of the extradata algorithm
        :return:
        """
        pass

    @property
    def description_short(self):
        """
        Short description of the extradata values
        :return:
        """
        pass

    @property
    def description_long(self):
        """
        Long description of the extradata, could include description of the data fields meanings
        :return:
        """
        pass

    @property
    def fields(self):
        """
        List of the extradata field names
        :return:
        """
        pass

    @property
    def __getitem__(self, item):
        """
        Gets extradata field by name
        :param item: field name
        :return: Pandas Series
        """
        pass
