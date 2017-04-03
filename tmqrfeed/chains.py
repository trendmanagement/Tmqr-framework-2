from collections import OrderedDict

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from tmqr.errors import ArgumentError, NotFoundError, ChainNotFoundError
from tmqr.settings import *
from tmqrfeed.contracts import FutureContract, ContractBase
import warnings
import datetime


class FutureChain:
    """
    Futures chain class
    """

    def __init__(self, fut_tckr_list, datamanager, rollover_days_before, futures_months, **kwargs):
        """
        Initiate Futures chain
        :param fut_tckr_list: list of futures contracts full-qualified tickers        
        :param datamanager: DataManager instance
        :param rollover_days_before: rollover in days before future contract expiration
        :param futures_months: list of tradable futures months
        :param kwargs: 
        """

        if fut_tckr_list is None or len(fut_tckr_list) == 0:
            raise ArgumentError("Failed to initiate futures chain empty tickers list")

        self.rollover_days_before = rollover_days_before
        if self.rollover_days_before is None:
            raise ArgumentError("'rollover_days_before' kwarg is not set")

        self.futures_months = futures_months
        if self.futures_months is None:
            raise ArgumentError("'futures_months' kwarg is not set")

        self.datamanager = datamanager

        if self.datamanager is None:
            raise ArgumentError("'datamanager' is None")

        self._futchain = self._generatechain_list(fut_tckr_list)

    def _generatechain_list(self, raw_futures):
        """
        Creates historical chains
        :param raw_futures:
        :return:
        """
        prev_fut = None
        date_start = QDATE_MIN

        chain = []

        for i, tckr in enumerate(raw_futures):
            fut = FutureContract(tckr, self.datamanager)

            #
            # Check expiration months filter
            #
            if fut.expiration_month not in self.futures_months:
                continue

            if prev_fut is None:
                prev_fut = fut
                continue
            else:
                series_date_start = prev_fut.expiration - BDay(self.rollover_days_before)
                series_date_end = fut.expiration - BDay(self.rollover_days_before)
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

    def get_list(self, date: datetime, offset: int = 0, limit: int = 0):
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
            raise ChainNotFoundError(
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
        """
        Get futures contracts list sorted by expiration date
        :return: 
        """
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
        """
        List of available expirations for options chains
        :return: 
        """
        return self._expirations

    def __iter__(self):
        for k, v in self.chain_list.items():
            yield v

    def items(self):
        for k, v in self.chain_list.items():
            yield k, v

    def find(self, date: datetime, by, **kwargs):
        """
        Find option chain by datetime, date, or offset
        If no **kwargs are set, performs exact match by datetime, date, or offset
        Otherwise if **kwargs are set, performs SMART search where 'by' must be current datetime
        :param date: current date
        :param by: lookup criteria
        :param kwargs:
            Keywords for SMART chains search:
            - min_days - ignore chains with days to expiration <= min_days
        :return:
        """
        if isinstance(by, datetime.datetime):
            return self.chain_list[by]
        elif isinstance(by, datetime.date):
            dt = datetime.datetime.combine(by, datetime.time(0, 0, 0))
            return self.chain_list[dt]
        elif isinstance(by, (int, np.int32, np.int64)):
            option_offset = by
            min_days = kwargs.get('min_days', 0)
            start_exp_idx = -1
            for i, exp in enumerate(self._expirations):
                if ContractBase.to_expiration_days(exp, date) > min_days:
                    start_exp_idx = i
                    break
            if start_exp_idx == -1:
                raise ChainNotFoundError(
                    f"Couldn't find not expired options chains, with days to expiration > {min_days}")

            if start_exp_idx + option_offset > len(self._expirations) - 1:
                raise ChainNotFoundError(
                    f"Couldn't find front+{option_offset} options chains, try to look next futures series",
                    # IMPORTANT: add valid series count here, this will help to handle next future chains by offset
                    option_offset_skipped=len(self._expirations) - start_exp_idx)

            expiration = self._expirations[start_exp_idx + option_offset]
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

        if len(self._strike_array) == 0:
            raise ChainNotFoundError(f'Empty option chain for {underlying} at expiration: {expiration}')

    @property
    def expiration(self):
        """
        Expiration date for option chain
        :return: 
        """
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
                        Search option contract by delta value:
                        If delta ==  0.5 - returns ATM call/put
                        If delta > 0.5 - returns ITM call/put near target delta
                        If delta < 0.5 - returns OTM call/put near target delta
        :param kwargs:
            * how == 'offset' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5) 
            * how == 'delta' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5)
                - strike_limit - how many strikes to analyse from ATM (default: 30)
        :return: OptionContract
        """
        if not isinstance(dt, datetime.datetime):
            raise ArgumentError("'dt' argument must be datetime")

        if opttype.upper() not in ('C', 'P'):
            raise ArgumentError("'opttype' argument must be 'C' or 'P'")

        if how == 'offset':
            if not isinstance(item, (int, np.int32, np.int64)):
                raise ArgumentError("'item' argument must be integer in the case of how=='offset'")

            err_limit = kwargs.get('error_limit', 5)
            return self._find_by_offset(dt, item, opttype.upper(), err_limit)
        if how == 'delta':
            if not isinstance(item, (float, np.float, np.double)):
                raise ArgumentError("'item' argument must be float in the case of how=='delta'")

            err_limit = kwargs.get('error_limit', 5)
            strike_limit = kwargs.get('strike_limit', 30)
            return self._find_by_delta(dt, item, opttype.upper(), err_limit, strike_limit)
        else:
            raise ArgumentError("Wrong 'how' argument, only 'offset'|'strike'|'delta' values supported.")

    def _get_atm_index(self, ulprice: float):
        """
        Find ATM index of strike array based on underlying price
        :param ulprice: underlying price
        :return: strike array index pointing to ATM strike
        """
        return int(np.argmin(np.abs(self._strike_array - ulprice)))

    def _find_by_delta(self, dt: datetime, delta: float, opttype: str, error_limit: int = 5, strike_limit: int = 30):
        """
        Search option contract by delta value:
        If delta ==  0.5 - returns ATM call/put
        If delta > 0.5 - returns ITM call/put near target delta
        If delta < 0.5 - returns OTM call/put near target delta
        :param dt: calculation date
        :param delta: delta to find (must be > 0 and < 1)
        :param opttype: option type 'C' or 'P'
        :param error_limit: how many consecutive QuoteNotFound errors occurred until ChainNotFoundError() raised
        :param strike_limit: how many strikes to analyse from ATM
        :return: Option contract instance 
        """

        delta = abs(delta)
        if delta <= 0 or delta >= 1 or np.isnan(delta):
            raise ArgumentError("Delta values must be > 0 and < 1")
        if strike_limit <= 0:
            raise ArgumentError("Only positive 'strike_limit' argument allowed")

        if delta == 0.5:
            return self._find_by_offset(dt, 0, opttype, error_limit=error_limit)

        # Fetching underlying price
        ul_decision_px, ul_exec_px = self.dm.price_get(self.underlying, dt)

        atm_index = self._get_atm_index(ul_decision_px)
        strikes_max_offset = len(self._strike_array) - atm_index - 1
        strikes_min_offset = -atm_index

        if opttype == 'P':
            # Algo direction for put
            offset_direction = 1 if delta > 0.5 else -1
            max_offset = abs(strikes_max_offset) if delta > 0.5 else abs(strikes_min_offset)
        else:
            # Algo direction for call
            offset_direction = 1 if delta < 0.5 else -1
            max_offset = abs(strikes_max_offset) if delta < 0.5 else abs(strikes_min_offset)

        i = offset_direction
        nerrors = 0
        last_contract = None
        while abs(i) <= min(strike_limit, max_offset):
            try:
                contract = self._find_by_offset(dt, i, opttype, error_limit=1)
                if (delta > 0.5 and abs(contract.delta(dt)) >= delta) or (
                                delta < 0.5 and abs(contract.delta(dt)) <= delta):
                    return contract
                last_contract = contract
                nerrors = 0
            except NotFoundError:
                # Catching data errors
                nerrors += 1
                if nerrors >= error_limit:
                    raise ChainNotFoundError(
                        f"Couldn't get requested strike by delta {delta} at {dt} for {self.underlying}."
                        f" QuoteNotFound errors limit reached: {nerrors} errors occurred.")
            i += offset_direction

        if last_contract is None:
            raise ChainNotFoundError(f"Couldn't get requested strike by delta {delta} at {dt}. Strike limit is reached."
                                     f" Try to check delta value validity and data presence for {self.underlying}.")

        return last_contract

    def _find_by_offset(self, dt: datetime, item: int, opttype: str, error_limit: int = 5):
        """
        Find option contract by offset from ATM
        :param dt: current datetime
        :param item: strike offset where 0 - ATM strike, +1 - ATM+1 strike above, -1 - ATM-1 strike below, etc...
        :param opttype: option type 'P' or 'C'
        :param error_limit: how many consecutive QuoteNotFound errors occurred until ChainNotFoundError() raised
        :return: OptionContract instance
        :rtype: OptionContract 
        """

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
                    raise ChainNotFoundError(f"Couldn't get requested strike offset at {dt} for {self.underlying}."
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
                            f"strikes {missing_options} is missing at {dt} for {self.underlying}.")
                else:
                    if item > 0:
                        item += 1
                    else:
                        item -= 1
