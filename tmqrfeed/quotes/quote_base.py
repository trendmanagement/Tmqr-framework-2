import pandas as pd

from tmqr.errors import ArgumentError
from tmqr.errors import QuoteEngineEmptyQuotes
from collections import OrderedDict

class QuoteBase:
    """
    Quotes making base class. Creates different kinds of quotes based on processing raw quotes.
    """

    def __init__(self, *args, **kwargs):
        self.dm = kwargs.get('datamanager', None)
        if self.dm is None:
            raise ArgumentError("'datamanager' kwarg is not set")

    def __str__(self):
        raise NotImplementedError("You must implement __str__() method in child QuoteEngine class")

    @staticmethod
    def merge_series(series_df_list):
        objs = [obj for obj in series_df_list if obj is not None]
        if len(objs) == 0:
            raise QuoteEngineEmptyQuotes("Built quotes series are empty. Insufficient time series in the DB?")

        merged_series = pd.concat(series_df_list)
        if len(merged_series) == 0:
            raise QuoteEngineEmptyQuotes("Built quotes series are empty. Insufficient time series in the DB?")
        return merged_series

    def build(self):
        """
        Execute quotes building
        :return: tuple pd.DataFrame Quotes, pd.Panel Positions
        """
        raise NotImplementedError("You must define this method in child class")
