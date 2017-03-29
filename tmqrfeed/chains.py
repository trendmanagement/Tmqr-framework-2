from collections import OrderedDict
from datetime import date

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from tmqr.errors import ArgumentError
from tmqr.settings import *
from tmqrfeed.contracts import FutureContract


class FutureChain:
    """
    Futures chain class
    """

    def __init__(self, fut_tckr_list, asset_info, datamanager, **kwargs):

        if fut_tckr_list is None or len(fut_tckr_list) == 0:
            raise ArgumentError("Failed to initiate futures chain empty tickers list")

        self.ainfo = asset_info
        self.rollover_days_before = kwargs.get('rollover_days_before', self.ainfo.rollover_days_before)
        default_fut_months = self.ainfo.get('futures_months', range(1, 12))
        self.futures_months = kwargs.get('futures_months', default_fut_months)
        self.date_start = kwargs.get('date_start', None)
        self.datamanager = datamanager

        self._futchain = self._generatechain_list(fut_tckr_list)

    def _generatechain_list(self, raw_futures):
        """
        Creates historical chains
        :param raw_futures:
        :return:
        """
        prev_fut = None
        date_start = QDATE_MIN if self.date_start is None else self.date_start

        chain = []

        for i, tckr in enumerate(raw_futures):
            fut = FutureContract(tckr, self.datamanager)
            if fut.exp_month not in self.futures_months:
                continue

            if prev_fut is None:
                prev_fut = fut
                continue
            else:
                series_date_start = prev_fut.exp_date - BDay(self.rollover_days_before)
                series_date_end = fut.exp_date - BDay(self.rollover_days_before)
                fut.series_date_start = series_date_start
                fut.series_date_end = series_date_end
                chain.append({
                    'ticker': fut,
                    'date_start': series_date_start,
                    'date_end': series_date_end,
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
        df = self._futchain[self._futchain.date_end > date]

        if offset < 0:
            raise ArgumentError("'offset' argument must be >= 0")
        elif offset > 0:
            df = df.shift(offset).dropna()

        if limit < 0:
            raise ArgumentError("'limit' argument must be > 0")
        elif limit > 0:
            df = df.head(limit)

        if len(df) == 0:
            raise ArgumentError("Can't get futures chain at {0} limit: {1} offset: {2}. "
                                "Too strict request or not enough data".format(date, limit, offset))

        return df

    def get_contract(self, date, offset=0):
        """
        Returns future contract for particular date
        :param date: actual date
        :param offset: chain offset, 0 - front chain, +1 - front+1, etc.
        :return: FutureContract class instance
        """
        df = self.get_list(date, offset, limit=1)
        return df.iloc[0].name

    def get_all(self):
        return self._futchain.index


class OptionChainList:
    """
    This class stores list of options chains with many expiration dates
    """

    def __init__(self, chain_list):
        if chain_list is None or len(chain_list) == 0:
            raise ArgumentError("Empty 'chain_list' argument")

        self.chain_list = OrderedDict()
        for c in chain_list:
            self.chain_list[c['_id']['date']] = OptionChain(c)

        self._expirations = sorted(list(self.chain_list.keys()))

    def __len__(self):
        return len(self.chain_list)

    @property
    def expirations(self):
        return self._expirations

    def __iter__(self):
        for k, v in self.chain_list.items():
            yield v

    def items(self):
        for k, v in self.chain_list.items():
            yield k, v

    def find(self, by, **kwargs):
        """
        Find option chain by datetime, date, or offset
        If no **kwargs are set, performs exact match by datetime, date, or offset
        Otherwise if **kwargs are set, performs SMART search where 'by' must be current datetime
        :param by: lookup criteria
        :param kwargs:
            Keywords for SMART chains search:
            - min_days - ignore chains with days to expiration <= min_days
        :return:
        """
        if len(kwargs) == 0:
            if isinstance(by, datetime):
                return self.chain_list[by]
            elif isinstance(by, date):
                dt = datetime.combine(by, datetime.min.time())
                return self.chain_list[dt]
            elif isinstance(by, (int, np.int32, np.int64)):
                expiration = self._expirations[by]
                return self.chain_list[expiration]
            else:
                raise ValueError('Unexpected item type, must be float or int')

    def __repr__(self):
        exp_str = ""

        for i, exp in enumerate(self.expirations):
            exp_str += '{0}: {1}\n'.format(i, exp.date())
        return exp_str


class OptionChain:
    """
    Main class for option chains data management.
    """

    def __init__(self, option_chain_record):
        self._expiration = option_chain_record['_id']['date']

    @property
    def expiration(self):
        return self._expiration
