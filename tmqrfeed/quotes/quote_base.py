import pandas as pd

from tmqr.errors import QuoteEngineEmptyQuotes


class QuoteBase:
    """
    Quotes making base class. Creates different kinds of quotes based on processing raw quotes.
    """

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
    def merge_positions(positions_df_list):
        valid_positions_count = 0

        for i in range(len(positions_df_list) - 1):
            j = -1
            last_date = None
            pos = positions_df_list[i]
            if positions_df_list[i] is None:
                continue
            valid_positions_count += 1

            while True:
                if abs(j) > len(pos):
                    break
                row = pos.iloc[j]
                if last_date is not None and last_date != row['date']:
                    break

                last_date = row['date']
                pos.at[row.name, 'qty'] = 0.0
                j -= 1
        if valid_positions_count == 0:
            return None
        else:
            return pd.concat(positions_df_list).set_index(['date'])

    def do_futref_checks(self):
        """
        Do extra sanity checks to make sure that old quotes are not changing when new data arrives, could be useful
        for some smart quotes algorithms.
        :return:
        """
        pass
