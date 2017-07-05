import warnings

from tmqr.errors import ArgumentError, SettingsError
from tmqr.settings import *
import pyximport
from math import isnan

pyximport.install()
from tmqrfeed.fast_option_pricing import blackscholes, blackscholes_greeks, GREEK_DELTA

FLOAT_NAN = float('nan')


class ContractBase:
    """
    Base class for generic asset
    """

    def __init__(self, tckr, datamanager=None, **kwargs):
        """
        Init generic contract from special `tckr` code

        :param tckr: Ticker code
        :param datamanager: DataManager instance
        """

        #: Full-qualified ticker name
        #: Examples:
        #: US.S.AAPL - US Apple inc. stock
        #: US.F.CL.M83.830520 - US Crude Oil future June 1983, expired at 1983-05-20
        #: US.C.F-CL-H11-110322.110121@89.0 - Call option on CLH11 future, expired at 2011-01-21, Strike 89.0
        self.ticker = tckr
        """Full-qualified ticker name"""

        self._toks = self._parse(self.ticker)
        if len(self._toks) < 3:
            raise ArgumentError("Contract ticker must contain at least 3 parts <Market>.<ContrType>.<Name>")

        #: Contract type, most common:
        #: 'F' - Future contract
        #: 'C' - Call option
        #: 'P' - Put option
        #: 'S' - Stock
        self.ctype = self._toks[1]
        """Contract type"""

        self.dm = datamanager
        """Global DataManager class instance"""

        self._point_value = None

    @property
    def instrument(self):
        """
        Contract's instrument in <Market>.<Name>

        :return:
        """
        return '{0}.{1}'.format(self.market, self.name)

    @property
    def market(self):
        """
        Contract's market

        :return:
        """
        return self._toks[0]

    @property
    def name(self):
        """
        Contract's name without market info

        :return:
        """
        return self._toks[2]

    @property
    def contract_info(self):
        """
        Return ContractInfo class values

        :return: ContractInfo class instance
        """
        return self.dm.datafeed.get_contract_info(self.ticker)

    @property
    def instrument_info(self):
        """
        Return underlying instrument info

        :return:
        """
        return self.dm.datafeed.get_instrument_info(self.instrument)

    @property
    def point_value(self):
        """
        1-point USD value

        :return: 
        """
        if self._point_value is None:
            iinfo = self.instrument_info
            if iinfo.ticksize == 0.0 or iinfo.tickvalue == 0.0:
                raise SettingsError(
                    f"'ticksize' or 'tickvalue' is not set in instrument {self.instrument} settings. "
                    f"Check the instrument settings in the DB")

            self._point_value = 1.0 / iinfo.ticksize * iinfo.tickvalue

        return self._point_value

    def dollar_pnl(self, prev_price, current_price, qty):
        """
        Calculate dollar PnL for asset

        :param prev_price: previous price
        :param current_price: current price
        :param qty:  
        :return: PnL in dollars
        """
        return (current_price - prev_price) * qty * self.point_value

    @staticmethod
    def calc_to_expiration_days(expiration_date, current_date):
        """
        Calculates calendar days to expiration

        :param expiration_date: 
        :param current_date: 
        :return: 
        """
        return (expiration_date.date() - current_date.date()).days

    def to_expiration_days(self, date):
        return 1000000000

    def delta(self, date):
        """
        Get contract delta

        :param date: 
        :return: decision time greeks
        """
        return 1.0

    def price(self, date, ulprice=None, iv_change=0.0, days_to_expiration=None, riskfreerate=None):
        """
        Calculate generic assets's price (also could be used for WhatIF analysis)

        :param date: 
        :param ulprice: 
        :param iv_change: 
        :param days_to_expiration: 
        :param riskfreerate: 
        :return: tuple (decision_price, execution_price)
        """
        return self.dm.price_get(self, date)

    def risk_free_rate(self, date):
        return self.dm.riskfreerate_get(self, date)


    @staticmethod
    def _parse(ticker):
        """
        Parses ticker and returns tokenized list of contract meta information

        :param ticker: special `tckr` code
        :return: list of tokens
        """
        if '@' in ticker:
            t, strike = ticker.split('@')
            res = t.split('.')
            res.append(strike)
            return res
        return ticker.split('.')

    def _parse_expiration(self, exp_string):
        """
        Expiration token parsing YYMMDD, if YY < 50 returns 2000s, otherwise 1900s

        :param exp_string: expiration strning YYMMDD
        :return: expiration datetime
        """
        if len(exp_string) != 6:
            raise ArgumentError("Expiration string must be 6 chars length: YYMMDD")
        y = int(exp_string[:2])
        if y < 50:
            y += 2000
        else:
            y += 1900
        try:
            m = int(exp_string[2:4])
            d = int(exp_string[-2:])
            return datetime(y, m, d)
        except ValueError:
            raise ArgumentError("Bad expiration sting for {0}".format(self.ticker))

    @property
    def data_source(self):
        raise NotImplementedError()

    def __str__(self):
        return self.ticker

    def __repr__(self):
        return self.ticker

    def __lt__(self, other):
        return self.ticker < other.ticker

    def __gt__(self, other):
        return self.ticker > other.ticker

    def __eq__(self, other):
        return self.ticker == self.ticker

    def __hash__(self):
        return self.ticker.__hash__()

    @classmethod
    def deserialize(cls, ticker, datamanager=None):
        idx_begin = ticker.find('.')
        idx_end = ticker.find('.', idx_begin + 1)
        ctype = ticker[idx_begin + 1:idx_end]

        if idx_begin == -1 or idx_end == -1 or ctype.strip() == '':
            raise ArgumentError(f"Couldn't parse contract type from {ticker}")

        if ctype == 'F':
            return FutureContract(ticker, datamanager)
        elif ctype == 'P' or ctype == 'C':
            return OptionContract(ticker, datamanager)
        else:
            return ContractBase(ticker, datamanager)


class FutureContract(ContractBase):
    """
    Future contract asset class
    """

    def __init__(self, tckr, datamanager=None, **kwargs):
        """
        Init future contract from special `tckr` code

        :param tckr: Ticker code
        :param datamanager: DataManager instance
        :param kwargs:            
        """
        super().__init__(tckr, datamanager)
        if self.ctype != 'F':
            raise ArgumentError("Contract type 'F' expected, but '{0}' given".format(self.ctype))
        if len(self._toks) != 5:
            raise ArgumentError("Future contract must have 5 tokens in ticker, like: US.F.CL.M83.830520")
        self.expiration = self._parse_expiration(self._toks[4])
        self.expiration_month = self._get_month_by_code(self._toks[3][0])

    @property
    def name(self):
        """
        Future contract name without market information, US.F.CL.M83.830520 -> CLM83

        :return:
        """
        return self._toks[2] + self._toks[3]

    @property
    def instrument(self):
        """
        Future contract instrument information: US.F.CL.M83.830520 -> US.CL

        :return:
        """
        return '{0}.{1}'.format(self.market, self._toks[2])

    @property
    def underlying(self):
        """
        Future contract underlying (equals to contract.instrument): US.F.CL.M83.830520 -> US.CL

        :return:
        """
        return self.instrument

    @staticmethod
    def _get_month_by_code(month_letter):
        """
        http://www.cmegroup.com/month-codes.html
        January	F
        February	G
        March	H
        April	J
        May	K
        June	M
        July	N
        August	Q
        September	U
        October	V
        November	X
        December	Z

        :param month_letter:
        :return:
        """
        month_letters = {
            'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6, 'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12}
        return month_letters[month_letter.upper()]

    @property
    def data_source(self):
        return self.instrument_info.data_futures_src

    def to_expiration_days(self, date):
        return super().calc_to_expiration_days(self.expiration, date)


class OptionContract(ContractBase):
    """
    Option contract asset class
    """

    def __init__(self, tckr, datamanager=None, **kwargs):
        """
        Init option contract from special `tckr` code

        :param tckr: Ticker code
        :param datamanager: DataManager instance
        :param kwargs: contract init kwargs
            * 'underlying' - underlying contract instance (by default: get from tckr name)
        """
        super().__init__(tckr, datamanager)
        if self.ctype != 'P' and self.ctype != 'C':
            raise ArgumentError("Contract type 'C' or 'P' expected, but '{0}' given".format(self.ctype))
        if len(self._toks) < 5 or len(self._toks) > 6:
            raise ArgumentError(
                "Option contract must have 5-6 tokens in ticker, like: US.C.F-ZB-H11-110322.110121[.OPTCODE]@89.0")

        self.expiration = self._parse_expiration(self._toks[3])
        if len(self._toks) > 5:
            # Handling case when contract ticker contains OPT_CODE
            self.strike = float(self._toks[5])
            self.opt_code = self._toks[4]
        else:
            self.strike = float(self._toks[4])
            self.opt_code = ''

        self._underlying = kwargs.get('underlying', None)
        self._pricing_context = None

    @property
    def name(self):
        """
        Option contract name without market information, US.C.F-ZB-H11-110322.110121@89.0 -> ZBH11.110121@89.0

        :return:
        """
        return '{0}.{1}@{2}'.format(self.underlying.name, self._toks[3], self._toks[4])

    @property
    def instrument(self):
        """
        Option contract instrument information: US.C.F-ZB-H11-110322.110121@89.0 -> US.ZB

        :return:
        """
        return self.underlying.instrument

    @property
    def underlying(self):
        """
        Option contract's underlying FutureContract class instance or ContractBase class instance.

        Example: US.C.F-ZB-H11-110322.110121@89.0 -> US.F.ZB.H11.110322 future instance
        US.C.S-AAPL.110121@89.0 -> US.S.AAPL for stock options

        :return: FutureContract class instance or ContractBase class instance
        """
        if self._underlying is None:
            underlying_name = '{0}.{1}'.format(self._toks[0], self._toks[2].replace('-', '.'))
            if self._toks[2].startswith('F-'):
                self._underlying = FutureContract(underlying_name, self.dm)
            else:
                self._underlying = ContractBase(underlying_name, self.dm)
        return self._underlying

    @property
    def point_value(self):
        """
        Point value of option contract
        :return:
        """
        if self._point_value is None:
            iinfo = self.instrument_info
            if iinfo.ticksize_options == 0.0 or iinfo.tickvalue_options == 0.0:
                raise SettingsError(
                    f"'ticksize_options' or 'tickvalue_options' is not set in instrument {self.instrument} settings. "
                    f"Check the instrument settings in the DB")

            self._point_value = 1.0 / iinfo.ticksize_options * iinfo.tickvalue_options

        return self._point_value

    @property
    def data_source(self):
        """
        DataSource name of OptionContract

        :return:
        """
        return self.instrument_info.data_options_src

    def set_pricing_context(self, date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv,
                            risk_free_rate=0.0):
        """
        Set recent date pricing context for option contract

        :param date: 
        :param ul_decision_px: 
        :param ul_exec_px: 
        :param option_decision_iv: 
        :param option_exec_iv: 
        :param risk_free_rate: 
        :return: 
        """
        self._pricing_context = (date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, risk_free_rate)

    def get_pricing_context(self, date):
        """
        Fetch pricing context for option contract from cache, otherwise from DataManager

        :param date: 
        :return: 
        """
        if self._pricing_context is not None and self._pricing_context[0] == date:
            # Trying to use cached pricing context
            return self._pricing_context

        # Fetching prices from data manager
        ul_decision_px, ul_exec_px = self.dm.price_get(self.underlying, date)
        option_decision_iv, option_exec_iv = self.dm.price_get(self, date)
        risk_free_rate = self.dm.riskfreerate_get(self, date)

        self.set_pricing_context(date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, risk_free_rate)
        return self._pricing_context

    def to_expiration_days(self, date):
        """
        Calendar days to option expiration

        :param date: 
        :return: 
        """
        return super().calc_to_expiration_days(self.expiration, date)

    def to_expiration_years_from_days(self, days_to_expiration):
        """
        Calculate years to expriration from days

        :param days_to_expiration: 
        :return: 
        """
        return (days_to_expiration * 24.0 * 60 * 60) / 31536000.0

    def _calc_price(self, ulprice, days_to_expiration, rfr, iv):
        """
        Price option contract using fast Black-Scholes algorithm

        :param ulprice: 
        :param days_to_expiration: 
        :param rfr: 
        :param iv: 
        :return: option price (float)
        """
        return blackscholes(1 if self.ctype == 'C' else 0, ulprice, self.strike,
                            self.to_expiration_years_from_days(days_to_expiration),
                            rfr, iv)

    def _calc_greeks(self, ulprice, days_to_expiration, rfr, iv):
        """
        Calculate greeks using fast Black-Scholes algorithm

        :param ulprice: 
        :param days_to_expiration: 
        :param rfr: 
        :param iv: 
        :return: 
        """
        return blackscholes_greeks(1 if self.ctype == 'C' else 0, ulprice, self.strike,
                                   self.to_expiration_years_from_days(days_to_expiration),
                                   rfr, iv)

    def iv(self, date):
        """
        Get option IV for date

        :param date: required date
        :return: decision time IV
        """
        context = self.get_pricing_context(date)
        return context[3]

    def delta(self, date):
        """
        Get option delta greek at the decision time

        :param date: 
        :return: decision time greeks
        """
        return self.greeks(date)[GREEK_DELTA]

    def greeks(self, date, ulprice=None, iv_change=0.0, days_to_expiration=None, riskfreerate=None):
        """
        Calculate option's greeks at the decision time  (only delta supported so far)

        :param date: 
        :param ulprice: 
        :param iv_change: 
        :param days_to_expiration: 
        :param riskfreerate: 
        :return: tuple (decision_price, execution_price)
        """
        date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, option_risk_free_rate = self.get_pricing_context(
            date)

        days_to_expiration = self.to_expiration_days(date) if days_to_expiration is None else days_to_expiration
        if days_to_expiration is not None:
            if days_to_expiration > self.to_expiration_days(date):
                warnings.warn(f"{self.ticker}: WhatIF days to expiration greater than current!", stacklevel=0)
        rfr = option_risk_free_rate if riskfreerate is None else riskfreerate

        option_greeks = self._calc_greeks(ul_decision_px if ulprice is None else ulprice,
                                          days_to_expiration,
                                          rfr,
                                          option_decision_iv + iv_change)

        return option_greeks

    def price(self, date, ulprice=None, iv_change=0.0, days_to_expiration=None, riskfreerate=None):
        """
        Calculate option's price (also could be used for WhatIF analysis)

        :param date: 
        :param ulprice: 
        :param iv_change: 
        :param days_to_expiration: 
        :param riskfreerate: 
        :return: tuple (decision_price, execution_price)
        """
        date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, option_risk_free_rate = self.get_pricing_context(
            date)

        days_to_expiration = self.to_expiration_days(date) if days_to_expiration is None else days_to_expiration
        if days_to_expiration is not None:
            if days_to_expiration > self.to_expiration_days(date):
                warnings.warn(f"{self.ticker}: WhatIF days to expiration greater than current!", stacklevel=0)
        rfr = option_risk_free_rate if riskfreerate is None else riskfreerate

        option_price_decision = self._calc_price(ul_decision_px if ulprice is None else ulprice,
                                                 days_to_expiration,
                                                 rfr,
                                                 option_decision_iv + iv_change)

        option_price_exec = self._calc_price(ul_exec_px if ulprice is None else ulprice,
                                             days_to_expiration,
                                             rfr,
                                             option_exec_iv + iv_change)

        assert not isnan(option_price_decision), f"Option decision price is NaN: {self.ticker} at {date} " \
                                                 f"UnderlyingPrice: {ul_decision_px if ulprice is None else ulprice} " \
                                                 f"DaysToExp: {days_to_expiration} RFR: {rfr} IV: {option_decision_iv + iv_change}"

        assert not isnan(option_price_decision), f"Option execution price is NaN: {self.ticker} at {date} " \
                                                 f"UnderlyingPrice: {ul_exec_px if ulprice is None else ulprice} " \
                                                 f"DaysToExp: {days_to_expiration} RFR: {rfr} IV: {option_exec_iv + iv_change}"

        return option_price_decision, option_price_exec
