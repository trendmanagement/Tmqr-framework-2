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

    @staticmethod
    def merge_series(series_df_list):
        objs = [obj for obj in series_df_list if obj is not None]
        if len(objs) == 0:
            raise QuoteEngineEmptyQuotes("Built quotes series are empty. Insufficient time series in the DB?")

        merged_series = pd.concat(series_df_list)
        if len(merged_series) == 0:
            raise QuoteEngineEmptyQuotes("Built quotes series are empty. Insufficient time series in the DB?")
        return merged_series

    @staticmethod
    def merge_positions(positions_list):
        valid_positions_count = 0
        result_positions = {}

        for i in range(len(positions_list)):
            j = -1
            last_date = None
            pos = positions_list[i]
            if positions_list[i] is None:
                continue
            valid_positions_count += 1

            if i < len(positions_list) - 1:
                # Implementing rollover for previous contracts
                while True:
                    if abs(j) > len(pos):
                        break
                    row = pos[j]
                    # 'row' is a tuple of: date, asset, decision_px, exec_px, qty
                    if last_date is not None and last_date != row[0]:
                        break
                    last_date = row[0]
                    # Re-constructing new tuple with 0.0 - qty field
                    pos[j] = (row[0], row[1], row[2], row[3], 0.0)
                    j -= 1

            # Filling positions_dictionary
            for p in pos:
                # 'p' is a tuple of: date, asset, decision_px, exec_px, qty
                date = p[0]
                asset = p[1]
                decision_px = p[2]
                exec_px = p[3]
                qty = p[4]

                assets_at_date_dict = result_positions.setdefault(date, {})

                # Checking that we don't have same asset records at the same date
                assert asset not in assets_at_date_dict

                # Saving prices and qty to dictionary
                assets_at_date_dict[asset] = (decision_px, exec_px, qty)

        if valid_positions_count == 0:
            return {}
        else:
            return result_positions

    def build(self):
        """
        Execute quotes building
        :return: tuple pd.DataFrame Quotes, pd.Panel Positions
        """
        raise NotImplementedError("You must define this method in child class")
