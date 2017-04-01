from collections import OrderedDict
from datetime import date, time

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from tmqr.errors import ArgumentError, NotFoundError, ChainNotFoundError
from tmqr.settings import *
from tmqrfeed.contracts import FutureContract, ContractBase


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
            raise ArgumentError(
                f"Can't get futures chain at {date} limit: {limit} offset: {offset}. Too strict request or not enough data")

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

    def __init__(self, chain_list, underlying: ContractBase, datamanager):
        if chain_list is None or len(chain_list) == 0:
            raise ArgumentError("Empty 'chain_list' argument")

        self.dm = datamanager
        if self.dm is None:
            raise ArgumentError("DataManager instance must be set")

        self.underlying = underlying


        if self.underlying is None:
            raise ArgumentError("Underlying asset in None")

        self.chain_list = OrderedDict()
        for expiration, chain in chain_list.items():
            self.chain_list[expiration] = OptionChain(chain, expiration, underlying, datamanager=self.dm)

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
                dt = datetime.combine(by, time(0, 0, 0))
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

    def __init__(self, option_chain_record, expiration: datetime, underlying: ContractBase, datamanager):
        self._expiration = expiration
        self.dm = datamanager
        self.underlying = underlying

        self._options = option_chain_record
        self._strike_array = np.array(list(self._options.keys()))

        if self.dm is None:
            raise ArgumentError("DataManager instance must be set")

    @property
    def expiration(self):
        return self._expiration

    def find(self, dt: datetime, item, opttype: str, how='offset', **kwargs):
        """
        Find option contract in chain using 'how' criteria
        :param dt: analysis date
        :param item: search value
        :param opttype: option type 'C' or 'P'
        :param how: search method
                    - 'offset' - by strike offset from ATM
                    - 'strike' - by strike absolute value
                    - 'delta'  - by delta                    
        :param kwargs:
            * how == 'offset' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5) 
        :return: OptionContract
        """
        if not isinstance(dt, datetime):
            raise ArgumentError("'dt' argument must be datetime")

        if opttype.upper() not in ('C', 'P'):
            raise ArgumentError("'opttype' argument must be 'C' or 'P'")


        if how == 'offset':
            if not isinstance(item, (int, np.int32, np.int64)):
                raise ArgumentError("'item' argument must be integer in the case of how=='offset'")

            limit = kwargs.get('error_limit', 5)
            return self._find_by_offset(dt, item, opttype.upper(), limit)
        else:
            raise ArgumentError("Wrong 'how' argument, only 'offset'|'strike'|'delta' values supported.")

    def _get_atm_index(self, ulprice: float):
        return np.argmin(np.abs(self._strike_array - ulprice))

    def _find_by_offset(self, dt: datetime, item: int, opttype: str, error_limit: int = 5):

        # Fetching underlying price
        ul_decision_px, ul_exec_px = self.dm.price_get(self.underlying, dt)

        atm_index = self._get_atm_index(ul_decision_px)

        initial_item = item

        #
        # Perform strike search by index
        #
        is_not_found = False
        while True:
            if initial_item != 0:
                nerrors = abs(item) - abs(initial_item)
                if nerrors >= error_limit:
                    raise ChainNotFoundError(f"Couldn't get requested strike offset at {dt}."
                                             f" QuoteNotFound errors limit reached: {nerrors} errors occurred.")

            if atm_index + item < 0 or atm_index + item > len(self._strike_array) - 1:
                if is_not_found:
                    raise ChainNotFoundError(f"Failed to find options quotes while processing chain at {dt}")
                else:
                    raise ChainNotFoundError(f"Strike offset is too low, "
                                             f"[{-atm_index}, {len(self._strike_array)-atm_index-1}] values allowed")

            strike = self._strike_array[atm_index + item]
            call_contract, put_contract = self._options[strike]
            try:
                # Getting Put/Call prices
                # To make sure that we have quotes available in the DB
                selected_option = call_contract if opttype == 'C' else put_contract

                # Getting option price to check data availability (rises 'NotFoundError' if not)
                # and populating pricing context for selected option
                opt_decision_iv, opt_exec_iv = self.dm.price_get(selected_option, dt)

                # Set pricing context for option, this prevents extra DB calls
                # Because we expect that selected option will be priced soon in the calling code
                selected_option.set_pricing_context(dt, ul_decision_px, ul_exec_px, opt_decision_iv, opt_exec_iv)
                return selected_option
            except NotFoundError:
                is_not_found = True
                # Searching next strike
                if initial_item == 0:
                    # If we need ATM strike we will perform bidirectional strike search
                    # If ATM options data is missing we will search ATM+1
                    # If ATM+1 still has no data we will search ATM-1
                    # If ATM-1 still has no data we will raise ChainNotFoundError()
                    if item == 0:
                        # Search for strike ATM+1
                        item = 1
                    elif item == 1:
                        # Search for strike ATM-1
                        item = -1
                    else:
                        missing_strikes = [self._strike_array[atm_index + x] for x in [-1, 0, 1]]
                        missing_options = [self._options[strike][0 if opttype == 'C' else 1] for strike in
                                           missing_strikes]
                        raise ChainNotFoundError(
                            f"Couldn't find ATM strike data, data for "
                            f"strikes {missing_options} is missing at {dt}.")
                else:
                    if item > 0:
                        item += 1
                    else:
                        item -= 1
