from datetime import datetime

import pandas as pd
from pandas.tseries.offsets import BDay

from tmqrfeed.contracts import FutureContract


class FutureChain:
    """
    Futures chain class
    """

    def __init__(self, fut_tckr_list, asset_info, **kwargs):

        if fut_tckr_list is None or len(fut_tckr_list) == 0:
            raise ValueError("Failed to initiate futures chain empty tickers list")

        self.ainfo = asset_info
        self.rollover_days_before = kwargs.get('rollover_days_before', self.ainfo.rollover_days_before)
        default_fut_months = self.ainfo.get('futures_months', range(1, 12))
        self.futures_months = kwargs.get('futures_months', default_fut_months)
        self.date_start = kwargs.get('date_start', None)

        raw_futures = [FutureContract(f) for f in fut_tckr_list]
        self.futchain = self._generate_chains(raw_futures)

    def _generate_chains(self, raw_futures):
        """
        Creates historical chains
        :param raw_futures:
        :return:
        """
        prev_fut = None
        date_start = datetime(1900, 1, 1) if self.date_start is None else self.date_start

        chain = []

        for i, fut in enumerate(raw_futures):
            if fut.exp_month not in self.futures_months:
                continue

            if prev_fut is None:
                prev_fut = fut
                continue
            else:
                chain.append({
                    'ticker': fut,
                    'date_start': prev_fut.exp_date - BDay(self.rollover_days_before - 1),
                    'date_end': fut.exp_date - BDay(self.rollover_days_before),
                })
                prev_fut = fut

        df = pd.DataFrame(chain).set_index('ticker')
        return df[df.date_end > date_start]

    def get_list(self, date, offset=0, limit=0):
        """
        Returns list of actual futures contracts for particular date
        :param date: actual date
        :param offset: chain offset, 0 - front chain, +1 - front+1, etc.
        :param limit: Number contracts to return (0 - all)
        :return: pd.DataFrame with chain information
        """
        df = self.futchain[self.futchain.date_end > date]

        if offset < 0:
            raise ValueError("'offset' argument must be >= 0")
        elif offset > 0:
            df = df.shift(offset).dropna()

        if limit < 0:
            raise ValueError("'limit' argument must be >= 0")
        elif limit > 0:
            df = df.head(limit)

        if len(df) == 0:
            raise ValueError("Can't get futures chain at {0} limit: {1} offset: {2}. "
                             "Too strict request or not enough data".format(date, limit, offset))

        return df

    def get(self, date, offset=0):
        """
        Returns future contract for particular date
        :param date: actual date
        :param offset: chain offset, 0 - front chain, +1 - front+1, etc.
        :return: FutureContract class instance
        """
        df = self.get_list(date, offset, limit=1)
        return df.iloc[0].name
