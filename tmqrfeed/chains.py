from collections import OrderedDict

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from tmqr.errors import ArgumentError, NotFoundError, ChainNotFoundError, QuoteNotFoundError
from tmqr.settings import *
from tmqrfeed.contracts import FutureContract, ContractBase, OptionContract
import warnings
import datetime
from typing import List, Tuple

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

        self._futchain = self._generatechain_list(
            fut_tckr_list)  # type: List[Tuple[FutureContract, datetime.datetime, datetime.datetime]]

    def _generatechain_list(self,
                            raw_futures: List[str]) -> List[
        Tuple[FutureContract, datetime.datetime, datetime.datetime]]:
        """
        Creates historical chains

        :param raw_futures:
        :return:
        """
        prev_fut = None

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
                chain.append((fut, series_date_start.date(), series_date_end.date()))
                prev_fut = fut

        return chain

    def _bisect_right(self,
                      fut_chain: List[Tuple[FutureContract, datetime.datetime, datetime.datetime]],
                      end_date: datetime.datetime) -> int:
        """Return the index where to insert item end_date in list fut_chain, assuming fut_chain is sorted.

        The return value i is such that all e in fut_chain[:i] have e <= end_date, and all e in
        fut_chain[i:] have e > end_date.  So if end_date already appears in the list, fut_chain.insert(end_date) will
        insert just after the rightmost end_date already there.

        Optional args lo (default 0) and hi (default len(fut_chain)) bound the
        slice of fut_chain to be searched.
        """
        lo = 0
        hi = len(fut_chain)

        while lo < hi:
            mid = (lo + hi) // 2
            if end_date < fut_chain[mid][2]:  # Slightly changed algo to fetch end date
                hi = mid
            else:
                lo = mid + 1
        return lo

    def get_list(self,
                 date: datetime.datetime,
                 offset: int = 0,
                 limit: int = 0) -> List[Tuple[FutureContract, datetime.datetime, datetime.datetime]]:
        """
        Returns list of actual futures contracts for particular date

        :param date: actual date
        :param offset: chain offset, 0 - front chain, +1 - front+1, etc.
        :param limit: Number contracts to return (0 - all)
        :return: List[Tuple[FutureContract, start_datetime, end_datetime]]
        """
        idx_start = self._bisect_right(self._futchain, date.date())


        if offset < 0:
            raise ArgumentError("'offset' argument must be >= 0")
        if limit < 0:
            raise ArgumentError("'limit' argument must be > 0")

        if limit > 0:
            result = self._futchain[idx_start + offset: idx_start + offset + limit]
        else:
            result = self._futchain[idx_start + offset:]

        if len(result) == 0:
            raise ChainNotFoundError(
                f"Can't get futures chain at {date} limit: {limit} offset: {offset}. Too strict request or not enough data")

        return result

    def get_contract(self, date: datetime.datetime, offset: int = 0) -> FutureContract:
        """
        Returns future contract for particular date

        :param date: actual date
        :param offset: chain offset, 0 - front chain, +1 - front+1, etc.
        :return: FutureContract class instance
        """
        df = self.get_list(date, offset, limit=1)
        return df[0][0]

    def get_all(self) -> List[Tuple[FutureContract, datetime.datetime, datetime.datetime]]:
        """
        Get futures contracts list sorted by expiration date

        :return: List[Tuple[FutureContract, datetime, datetime]]
        """
        return self._futchain


class OptionChain:
    """
    Main class for option chains data management.
    """

    def __init__(self, option_chain_record, expiration: datetime.datetime, underlying: ContractBase, datamanager):
        self._expiration = expiration
        self.dm = datamanager
        self.underlying = underlying

        self._options = option_chain_record
        self._strike_array = np.array(list(self._options.keys()))

        if self.dm is None:
            raise ArgumentError("DataManager instance must be set")

        if len(self._strike_array) == 0:
            raise ChainNotFoundError(f'Empty option chain for {underlying} at expiration: {expiration}')

        # Setting chain opt code
        opt_code_set = set()
        for call, put in self._options.values():
            opt_code_set.add(call.opt_code)
            opt_code_set.add(put.opt_code)

        if len(opt_code_set) > 1:
            raise ArgumentError(
                f"Mixed options codes for {underlying} option chain at expiration {expiration}: {opt_code_set}")

        self.opt_code = opt_code_set.pop()

    @property
    def expiration(self) -> datetime.datetime:
        """
        Expiration date for option chain
        :return:
        """
        return self._expiration

    def find(self,
             dt: datetime.datetime,
             item,
             opttype: str,
             how='offset',
             **kwargs) -> OptionContract:
        """
        Find option contract in chain using 'how' criteria

        :param dt: analysis date
        :param item: search value ( depending on 'how' parameter value required ATM offset, absolute strike price or delta )
        :param opttype: option type 'C' or 'P'
        :param how: search method

            * 'offset' - by strike offset from ATM
            * 'delta'  - by delta
                Search option contract by delta value:
                    - If delta ==  0.5 - returns ATM call/put
                    - If delta > 0.5 - returns ITM call/put near target delta
                    - If delta < 0.5 - returns OTM call/put near target delta
        :param kwargs:
            * how == 'offset' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5)
            * how == 'delta' kwargs:
                - error_limit - how many QuoteNotFound errors occurred before raising exception (default: 5)
                - strike_limit - how many strikes to analyse from ATM (default: 30)
        :return: OptionContract

        Examples::

            # Getting actual options chain (to get more info refer to DataManager.chains_options_get() help)
            fut, opt_chain = self.dm.chains_options_get('US.ES', dt)


            dt = datetime(2017, 3, 2)
            #
            # Getting option contracts from chain by ATM offset

            # ATM Put (all of these lines are equivalent)
            atm_put = opt_chain.find(dt, item=0, opttype='P', how='offset' )
            atm_put = opt_chain.find(dt, item=0, opttype='P')
            atm_put = opt_chain.find(dt, 0, 'P')

            # ATM + 1 Strike above call
            atm_call_up1 = opt_chain.find(dt, 1, 'C')
            # ATM - 1 Strike above call
            atm_call_dn1 = opt_chain.find(dt, -1, 'C')

            #
            # Getting options by delta
            #
            # - If delta ==  0.5 - returns ATM call/put
            # - If delta > 0.5 - returns ITM call/put near target delta
            # - If delta < 0.5 - returns OTM call/put near target delta
            #

            # ATM Put option
            atm_put = opt_chain.find(dt, item=0.5, opttype='P', how='delta')

            # 0.25 Delta OTM option
            otm_put = opt_chain.find(dt, item=0.25, opttype='P', how='delta')

            # 0.75 Delta ITM option
            itm_put = opt_chain.find(dt, item=0.75, opttype='P', how='delta')


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
            raise ArgumentError("Wrong 'how' argument, only 'offset'|'delta' values supported.")

    def _get_atm_index(self, ulprice: float) -> int:
        """
        Find ATM index of strike array based on underlying price
        :param ulprice: underlying price
        :return: strike array index pointing to ATM strike
        """
        return int(np.argmin(np.abs(self._strike_array - ulprice)))

    def _find_by_delta(self,
                       dt: datetime,
                       delta: float,
                       opttype: str,
                       error_limit: int = 5,
                       strike_limit: int = 30) -> OptionContract:
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
                contract = self._find_by_offset(dt, i, opttype,
                                                error_limit=1,
                                                ul_decision_px=ul_decision_px,
                                                ul_exec_px=ul_exec_px)
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

    def _find_by_offset(self,
                        dt: datetime,
                        item: int,
                        opttype: str,
                        error_limit: int = 5,
                        ul_decision_px=None,
                        ul_exec_px=None) -> OptionContract:
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
        if ul_decision_px is None or ul_exec_px is None:
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

                rfr = self.dm.riskfreerate_get(selected_option, dt)

                # Set pricing context for option, this prevents extra DB calls
                # Because we expect that selected option will be priced soon in the calling code
                selected_option.set_pricing_context(dt, ul_decision_px, ul_exec_px, opt_decision_iv, opt_exec_iv, rfr)
                return selected_option
            except QuoteNotFoundError:
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

    def __str__(self):
        return f'Chain: {self.underlying} {self.expiration.date()}'

    def __repr__(self):
        return self.__str__()

class OptionChainList:
    """
    This class stores list of options chains with many expiration dates
    """

    def __init__(self, chain_list, underlying: ContractBase, datamanager):
        """
        Init OptionChainList class
        :param chain_list: chain list dictionary
        :param underlying: underlying contract
        :param datamanager: DataManager instance
        """
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

        self._expirations = sorted(list(self.chain_list.keys()))  # type: List[datetime.datetime]

    def __len__(self):
        return len(self.chain_list)

    @property
    def expirations(self) -> List[datetime.datetime]:
        """
        List of available expirations for options chains

        :return: List[datetime.datetime]
        """
        return self._expirations

    def __iter__(self):
        for k, v in self.chain_list.items():
            yield v

    def items(self):
        """
        Key-value iterator where Key is expiration date of chain and Value is OptionChain class instance

        :return: yields expiration, OptionsChain
        """
        for k, v in self.chain_list.items():
            yield k, v

    def find(self, date: datetime.datetime, by, **kwargs) -> OptionChain:
        """
        Find option chain by datetime, date, or offset

        If no **kwargs are set, performs exact match by datetime, date, or offset

        Otherwise if **kwargs are set, performs SMART search where 'by' must be current datetime

        :param date: current date
        :param by: lookup criteria
        :param kwargs:
            Keywords for SMART chains search:
            - min_days - ignore chains with days to expiration <= min_days
            - opt_codes - include only option chains in opt_codes list
        :return:
        """
        if isinstance(by, datetime.datetime):
            return self.chain_list[by]
        elif isinstance(by, datetime.date):
            dt = datetime.datetime.combine(by, datetime.time(0, 0, 0))
            return self.chain_list[dt]
        elif isinstance(by, (int, np.int32, np.int64)):
            option_offset = by

            if option_offset < 0:
                raise ArgumentError("'by' must be >= 0")

            min_days = kwargs.get('min_days', 0)
            start_exp_idx = -1
            for i, exp in enumerate(self._expirations):
                if ContractBase.calc_to_expiration_days(exp, date) > min_days:
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

            opt_codes = kwargs.get('opt_codes', [])
            if opt_codes:
                oc_i = start_exp_idx
                oc_cnt = 0
                while True:
                    if oc_i > len(self.expirations) - 1:
                        raise ChainNotFoundError(
                            f"Couldn't find front+{option_offset} options chains, filtered by opt_codes {opt_codes}",
                            # IMPORTANT: add valid series count here, this will help to handle next future chains by offset
                            option_offset_skipped=oc_cnt)
                    expiration = self._expirations[oc_i]
                    chain = self.chain_list[expiration]
                    if chain.opt_code in opt_codes:
                        if oc_cnt == option_offset:
                            break
                        oc_cnt += 1
                    oc_i += 1
            else:
                expiration = self._expirations[start_exp_idx + option_offset]
                chain = self.chain_list[expiration]

            return chain
        else:
            raise ArgumentError("Unexpected 'by' type, must be float or int")

    def __repr__(self):
        exp_str = f"{self.underlying} expirations list: \n"

        for i, exp in enumerate(self.expirations):
            _opt_code = self.chain_list[exp].opt_code
            if _opt_code:
                exp_str += '{0}: {1} (OptCode: {2})\n'.format(i, exp.date(), _opt_code)
            else:
                exp_str += '{0}: {1}\n'.format(i, exp.date())
        return exp_str



