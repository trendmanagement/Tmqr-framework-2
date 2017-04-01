import warnings

from tmqr.errors import ArgumentError
from tmqr.settings import *
from tmqrfeed.fast_option_pricing import blackscholes

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

        self.series_date_start = kwargs.get('date_start', QDATE_MIN)
        self.series_date_end = kwargs.get('date_end', QDATE_MAX)

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
        self.exp_date = self._parse_expiration(self._toks[4])
        self.exp_month = self._get_month_by_code(self._toks[3][0])

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
            - 'underlying' - underlying contract instance
        """
        super().__init__(tckr, datamanager)
        if self.ctype != 'P' and self.ctype != 'C':
            raise ArgumentError("Contract type 'C' or 'P' expected, but '{0}' given".format(self.ctype))
        if len(self._toks) != 5:
            raise ArgumentError("Option contract must have 5 tokens in ticker, like: US.C.F-ZB-H11-110322.110121@89.0")

        self.exp_date = self._parse_expiration(self._toks[3])
        self.strike = float(self._toks[4])

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
    def data_source(self):
        return self.instrument_info.data_options_src

    def set_pricing_context(self, date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv,
                            risk_free_rate=0.0):
        self._pricing_context = (date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, risk_free_rate)

    def get_pricing_context(self, date):
        if self._pricing_context is not None and self._pricing_context[0] == date:
            # Trying to use cached pricing context
            return self._pricing_context

        # Fetching prices from data manager
        ul_decision_px, ul_exec_px = self.dm.price_get(self.underlying, date)
        option_decision_iv, option_exec_iv = self.dm.price_get(self, date)
        # TODO: get riskfree rate from DataManager
        risk_free_rate = 0.0

        self.set_pricing_context(date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, risk_free_rate)
        return self._pricing_context

    def to_expiration_days(self, date):
        return (self.exp_date.date() - date.date()).days

    def to_expiration_years_from_days(self, days_to_expiration):
        return (days_to_expiration * 24.0 * 60 * 60) / 31536000.0

    def _calc_price(self, ulprice, days_to_expiration, rfr, iv):
        return blackscholes(1 if self.ctype == 'C' else 0, ulprice, self.strike,
                            self.to_expiration_years_from_days(days_to_expiration),
                            rfr, iv)

    def price(self, date, ulprice=None, iv_change=0.0, days_to_expiration=None, riskfreerate=None):
        date, ul_decision_px, ul_exec_px, option_decision_iv, option_exec_iv, option_risk_free_rate = self.get_pricing_context(
            date)

        days_to_expiration = self.to_expiration_days(date) if days_to_expiration is None else days_to_expiration
        if days_to_expiration is not None:
            if days_to_expiration > self.to_expiration_days(date):
                warnings.warn(f"{self.ticker}: WhatIF days to expiration greater than current!", stacklevel=0)
        rfr = option_risk_free_rate if riskfreerate is None else riskfreerate

        ulprice = ul_decision_px if ulprice is None else ulprice
        iv = option_decision_iv + iv_change

        option_price_decision = self._calc_price(ulprice, days_to_expiration, rfr, iv)

        ulprice = ul_exec_px if ulprice is None else ulprice
        iv = option_exec_iv + iv_change
        option_price_exec = self._calc_price(ulprice, days_to_expiration, rfr, iv)

        return option_price_decision, option_price_exec
