from tmqr.errors import *
from tmqrfeed.contracts import ContractBase, FutureContract
from tmqrfeed.datafeed import DataFeed
from datetime import datetime
from tmqr.settings import QDATE_MIN, QDATE_MAX
from tmqrfeed.costs import Costs
from tmqr.logs import log
import pandas as pd
from typing import Dict, List, Tuple
from tmqrfeed import Position
from tmqrfeed.chains import FutureChain, OptionChain, OptionChainList
from math import isnan
from tmqrfeed.assetsession import AssetSession
import pytz


class DataManager:
    """
    Utility class used for data management of the strategy. 
    Also this class will be used for following purposes:
    * Quotes building - acts as a container for a different quotes types produced by Quote* classes.
    * Quotes aligning - if several quotes sources utilized with different timestamps layout
    * Return positions structure - contracts names and information for each date of the dataseries
    * Quotes sanity checks - warns if one of the series are delayed or has data holes
    * Data access interface and container - stores all data requested by strategies/contracts and provides interface for data management
    * Smart chains fetching - selects actual options and futures chains by several criterias
    * Quotes caching - reduces DB calls and speedup data access if this data is already fetched 
    * Extradata fetching - fetch extradata (like indexes or non-price data) from the DB and properly align this data    
    """

    def __init__(self, **kwargs):
        """
        Init DataManager class
        :param kwargs: 
        """
        # Initiate low-level datafeed
        feed = kwargs.get('datafeed', None)
        if feed is None:
            datafeed_cls = kwargs.pop('datafeed_cls', DataFeed)
            feed = datafeed_cls(**kwargs, datamanager=self)

        self.datafeed = feed  # type: DataFeed
        """DataFeed instance for low-level data fetching"""

        # Quotes dataframe for primary series
        self._primary_quotes = None  # type: pd.DataFrame
        # Secondary dataframes dictionary for secondary series quotes
        self._secondary_quotes = {}  # type: Dict[str, pd.DataFrame]

        # Quotes range settings
        self._quotes_range_start = None
        self._quotes_range_end = None

        # Primary series positions
        self._primary_positions = None
        # Secondary series positions dictionary
        self._secondary_positions = {}

        # Internal price cache for getting single quotes
        self._cache_single_price = {}

        self._cache_costs = {}  # type: Dict[str, Costs]

        # Actual session
        self._session = None  # type: AssetSession

    def session_get(self) -> AssetSession:
        """
        Returns trading session for all DataManager quotes, session settings should be set by call of the
        datamanager.session_set(...) method.
        :return:
        """
        if self._session is None:
            raise SettingsError("Session is not set, call datamanager.session_set(...) first.")

        return self._session

    def session_set(self,
                    instrument=None,
                    session_instance=None,
                    session_list=None,
                    tz=None) -> AssetSession:
        """
        Set the default trading session. This method intended to be used in the setup() method of Index and Alpha algorithms.

        Mode 1: Instrument based
            Load instrument (or market default) session from the DB by instrument name (example: 'US.ES')
        Mode 2: Custom session
            To initiate custom session, you should set the BOTH 'session_list' and 'tz' params (and exclude instrument param)

        'instrument' and (both 'session_list' and 'tz') parameters are mutually exclusive

        :param instrument: Full qualified name of the instrument to load from the DB (like 'US.ES')
        :param session_instance: AssetSession class instance
        :param session_list: list of the session params
            Example:
                session_list = [
                    # Default session
                    {
                    'decision': '10:40',             # Decision time (uses 'tz' param time zone!)
                    'dt': datetime(1900, 12, 31),    # Actual date of default session start
                    'execution': '10:45',            # Execution time (uses 'tz' param time zone!)
                    'start': '03:32'                 # Start of the session time (uses 'tz' param time zone!)
                    },

                    # If session rules has been changed by exchange, you can set different rules
                    {
                    'decision': '11:40',             # Decision time (uses 'tz' param time zone!)
                    'dt': datetime(2010, 12, 31),    # Actual date of new session rules start
                    'execution': '11:45',            # Execution time (uses 'tz' param time zone!)
                    'start': '01:32'                 # Start of the session time (uses 'tz' param time zone!)
                    },
                ]
        :param tz: see 'pytz' package's list of available timezones
        :return: AssetSession instance
        """
        if self._session is not None:
            raise SettingsError("Session has been already set, it's not allowed to set multiple sessions "
                                "per Index/Alpha instance, if you need to setup multi-instrumental session try to "
                                "apply universal trading session for all instruments")

        if instrument is not None:
            # Load instrument based session settings from the DB
            if session_list is not None or tz is not None or session_instance is not None:
                raise SettingsError(
                    "'instrument' and ('session_list' and 'tz') and 'session_instance' parameters are mutually exclusive")

            iinfo = self.datafeed.get_instrument_info(instrument)
            self._session = iinfo.session
            return self._session
        if session_instance is not None:
            if session_list is not None or tz is not None:
                raise SettingsError(
                    "'instrument' and ('session_list' and 'tz') and 'session_instance' parameters are mutually exclusive")

            assert isinstance(session_instance, AssetSession), 'session_instance expected to be AssetSession'
            self._session = session_instance
            return self._session

        elif session_list is not None and tz is not None:
            # Apply custom session settings for
            try:
                time_zone = pytz.timezone(tz)
                self._session = AssetSession(session_list, time_zone)
                return self._session
            except pytz.UnknownTimeZoneError:
                raise SettingsError(f"Unknown or unsupported timezone '{tz}'")
        else:
            raise SettingsError(
                "You should set 'instrument' or both 'session_list' and 'tz' to initiate session settings")


    def costs_set(self, market: str, costs: Costs) -> None:
        """
        Initiate costs settings for position PnL calculations
        :param market: market name
        :param costs: Costs class instance
        :return: 
        """
        if not isinstance(costs, Costs):
            raise ArgumentError("'costs' argument must be instance/or derived from tmqrfeed.costs.Costs class")
        self._cache_costs[market] = costs

    def costs_get(self, asset: ContractBase, qty: float) -> float:
        """
        Calculate costs based on 'asset'.market and qty
        :param asset: ContractBase instance
        :param qty: transaction qty
        :return: costs value in dollars
        """
        costs = self._cache_costs.get(asset.market, None)
        if not costs:
            raise CostsNotFoundError(f"Couldn't find costs settings for market '{asset.market}'."
                                     f"Try call datamanager.costs_set('market_name', costs_class_instance first.")
        return costs.calc_costs(asset, qty)

    def series_primary_set(self, quote_engine_cls, *args, **kwargs) -> None:
        """
        Fetch main series used for algorithm and strategy calculations
        :param quote_engine_cls: Quote* class
        :param args: positional arguments for given Quote* class
        :param kwargs: kwargs for given Quote* class
        :return: None
        """
        if self._primary_quotes is not None:
            raise DataManagerError("series_primary_set() already called, only one instance of primary quotes allowed")

        kwargs['datamanager'] = self

        quote_engine = quote_engine_cls(*args, **kwargs)
        self._primary_quotes, self._primary_positions = quote_engine.build()

    def series_extra_set(self, name, quote_engine_cls, *args, **kwargs) -> None:
        """
        Fetch additional series, align them to primary series and save by 'name'
        :param name: Extra series name for further access
        :param quote_engine_cls: Quote* class
        :param args: positional arguments for given Quote* class
        :param kwargs: kwargs for given Quote* class
        :return: None 
        """
        if self._primary_quotes is None:
            # Make sure that primary quotes are filled before
            raise DataManagerError("Call series_primary_set() before series_extra_set()")

        if name in self._secondary_quotes or name in self._secondary_positions:
            # Check for 'name' duplicate for extra series
            raise DataManagerError(f"You have already added extra series with name '{name}'")

        kwargs['datamanager'] = self
        quote_engine = quote_engine_cls(*args, **kwargs)
        quotes, pos = quote_engine.build()

        # Checking quotes validity
        if self.series_check(f"{quote_engine}_{name}", self._primary_quotes, quotes):
            # Align and store extra series
            self._secondary_quotes[name] = self.series_align(self._primary_quotes, quotes)
        self._secondary_positions[name] = pos

    def quotes(self, series_key: str = None) -> pd.DataFrame:
        """
        Get aligned primary or extra quotes data
        :param series_key: extra_series key, or if None - return primary series
        :return: pd.DataFrame of series
        """

        if series_key is None:
            if self._primary_quotes is None:
                raise QuoteNotFoundError("Primary quotes are not initiated, run series_primary_set() first")
            result_series = self._primary_quotes
        else:
            extra_series = self._secondary_quotes.get(series_key, None)
            if extra_series is None:
                raise QuoteNotFoundError(f"Couldn't find extra quotes by 'series_key'='{series_key}',"
                                         f" run series_extra_set() first or check the 'series_key' validity")
            result_series = extra_series

        if self._quotes_range_start is not None or self._quotes_range_end is not None:
            # Apply quote range filters
            result_series = result_series.ix[self._quotes_range_start:self._quotes_range_end]

        return result_series

    def quotes_range_set(self, range_start: datetime = None, range_end: datetime = None) -> None:
        """
        Set quotes date range returned by DataManager.quotes() method
        :param range_start: starting date
        :param range_end: end date
        :return: nothing
        """
        if range_start is not None and not isinstance(range_start, datetime):
            raise ArgumentError(f"'range_start' parameter expected to be datetime, got {type(range_start)}")

        if range_end is not None and not isinstance(range_end, datetime):
            raise ArgumentError(f"'range_start' parameter expected to be datetime, got {type(range_end)}")

        if range_end is not None and range_start is not None and range_end <= range_start:
            raise ArgumentError(f"'range_start' must be less than 'range_end'")

        self._quotes_range_start = range_start
        self._quotes_range_end = range_end

    def position(self, position_key: str = None) -> Position:
        """
        Get aligned primary or extra position instance
        :param position_key: extra_series key, or if None - return primary series
        :return: pd.DataFrame of series
        """
        if position_key is None:
            if self._primary_positions is None:
                raise PositionNotFoundError("Primary position is not initiated, try to run series_primary_set() first"
                                            " or make sure that Quote algorithm supports position initiation")
            return self._primary_positions
        else:
            try:
                return self._secondary_positions[position_key]
            except KeyError:
                raise PositionNotFoundError(f"Couldn't find extra position by 'position_key'='{position_key}',"
                                            f" run series_extra_set() first or check the 'position_key' validity")

    @staticmethod
    def series_align(primary_quotes: pd.DataFrame, extra_quotes: pd.DataFrame):
        return extra_quotes.reindex(primary_quotes.index, method='ffill')

    @staticmethod
    def series_check(name: str, primary_quotes: pd.DataFrame, extra_quotes: pd.DataFrame) -> bool:
        if extra_quotes is None:
            log.warn(f"ExtraSeriesSanityCheck: '{name}' - extra quotes are None")
            return False
        if not isinstance(extra_quotes, pd.DataFrame):
            log.warn(f"ExtraSeriesSanityCheck: '{name}' - extra quotes are not Pandas.DataFrame")
            return False

        if len(extra_quotes) == 0:
            log.warn(f"ExtraSeriesSanityCheck: '{name}' - extra quotes are empty")
            return False

        if primary_quotes.index[0] > extra_quotes.index[-1] or primary_quotes.index[-1] < extra_quotes.index[0]:
            log.warn(f"ExtraSeriesSanityCheck: '{name}' - extra quotes period doesn't overlap with primary quotes")
            return False

        if (primary_quotes.index[-1] - extra_quotes.index[-1]).days >= 1:
            log.warn(f"ExtraSeriesSanityCheck: '{name}' - extra quotes could be delayed. "
                     f"Primary last date: {primary_quotes.index[-1]} Extra last date: {extra_quotes.index[-1]}")

        return True

    def series_get(self, asset: ContractBase, **kwargs) -> pd.DataFrame:
        """
        Get asset's raw series from the DB
        :param asset: asset instance
        :param kwargs: DataFeed get_raw_series() **kwargs
        :return: series DataFrame
        """
        kw_source_type = kwargs.get('source_type', asset.data_source)
        kw_date_start = kwargs.get('date_start', QDATE_MIN)
        kw_date_end = kwargs.get('date_end', QDATE_MAX)

        # use default session timezone
        kw_timezone = self.session_get().tz

        return self.datafeed.get_raw_series(asset.ticker,
                                            source_type=kw_source_type,
                                            timezone=kw_timezone,
                                            date_start=kw_date_start,
                                            date_end=kw_date_end
                                            )

    def riskfreerate_get(self, asset: ContractBase, date: datetime) -> float:
        rfr_series = self.datafeed.get_riskfreerate_series(asset.market)

        try:
            # Trying to go fastest way
            return rfr_series[date.date()]
        except KeyError:
            # Getting closest risk-free rate
            closest_rfr = rfr_series.ix[:date.date()].tail(1)
            if len(closest_rfr) == 0:
                raise QuoteNotFoundError(f"Risk-free rate data point not found for '{asset.market}' market at {date}")
            return closest_rfr[0]

    def price_get(self, asset: ContractBase, date: datetime, **kwargs) -> Tuple[float, float]:
        """
        Get price at decision and execution time for given asset
        :param asset: Contract class instance
        :param date: timestamp for price
        :return: Tuple of [decision_px, exec_px]
        """

        # Check if asset is expired
        if asset.to_expiration_days(date) < 0:
            raise AssetExpiredError(f"Trying to get price for already expired asset: {asset} at {date}")

        # Trying to search positions cache
        res = self._price_get_positions_cached(asset, date)
        if res[0] is not None:
            return res

        # Trying to search internal price cache
        res = self._price_get_cached(asset, date)
        if res[0] is not None:
            return res

        res = self._price_get_from_datafeed(asset, date, **kwargs)

        #
        # Check for price validity
        #
        if isnan(res[0]) or isnan(res[1]):
            raise QuoteNotFoundError(f"NaN price returned by datafeed for {asset} at {date}")

        self._price_set_cached(asset, date, res)

        return res

    def _price_get_positions_cached(self, asset: ContractBase, date: datetime):

        # Looking for primary positions
        if self._primary_positions is not None:
            try:
                return self._primary_positions.get_asset_price(date, asset)
            except PositionQuoteNotFoundError:
                pass

        # TODO: add look up for secondary data positions
        return None, None

    def _price_get_cached(self, asset: ContractBase, date):
        """
        Check internal price cache for asset's price
        :param asset: 
        :param date: 
        :return: 
        """
        if type(asset) == FutureContract or type(asset) == ContractBase:
            price_data_dict = self._cache_single_price.get(asset, None)
            if price_data_dict is not None:
                price_data = price_data_dict.get(date, None)
                if price_data is not None:
                    return price_data
        return None, None

    def _price_set_cached(self, asset: ContractBase, date, price_data):
        """
        Populate internal cache
        :param asset: 
        :param date: 
        :param price_data:
        :return: 
        """
        if type(asset) == FutureContract or type(asset) == ContractBase:
            price_data_dict = self._cache_single_price.setdefault(asset, {})
            price_data_dict[date] = price_data

    def _price_get_from_datafeed(self, asset: ContractBase, date, **kwargs):
        """
        Fetch asset price directly from datafeed
        :return: 
        """
        iinfo = asset.instrument_info
        kw_source_type = kwargs.get('source_type', asset.data_source)
        kw_data_options_use_prev_date = kwargs.get('data_options_use_prev_date', iinfo.data_options_use_prev_date)

        session = self.session_get()
        # Use default session timezone to maintain data granularity
        kw_timezone = session.tz

        sess_start_time, sess_decision_time, sess_execution_time, next_sess_date = session.get(date)

        decision_px, exec_px = self.datafeed.get_raw_prices(asset.ticker,
                                                            source_type=kw_source_type,
                                                            dt_list=[sess_decision_time, sess_execution_time],
                                                            timezone=kw_timezone,
                                                            date_start=sess_decision_time,
                                                            date_end=sess_execution_time,
                                                            data_options_use_prev_date=kw_data_options_use_prev_date
                                                            )

        return decision_px, exec_px

    def chains_futures_get(self, instrument: str, date: datetime, offset: int = 0) -> FutureContract:
        """
        Get future contract from futures chains
        :param instrument: Full-qualified instrument name
        :param date: current date 
        :param offset: future expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
        :return: Future contract
        """
        fut_chain = self.datafeed.get_fut_chain(instrument)
        return fut_chain.get_contract(date, offset)

    def chains_options_get(self, instrument: str, date: datetime, **kwargs) -> Tuple[FutureContract, OptionChain]:
        """
        Find future+option chain by given criteria
        :param instrument: Full-qualified instrument name
        :param date: current date
        :param kwargs: 
            - 'opt_offset' - option expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
            - 'opt_min_days' - minimal days count until option expiration (default: 2)
            - 'opt_codes' - include options codes only (default: [] i.e. include all)
            - 'error_limit' - ChainNotFoundError error limit, useful to increase when you are trying to get far 'opt_offset' (default: 4)
        :return: (tuple) FutureContract, OptionChain
        """

        opt_offset = kwargs.get('opt_offset', 0)
        opt_min_days = kwargs.get('opt_min_days', 2)
        opt_codes = kwargs.get('opt_codes', [])
        error_limit = kwargs.get('error_limit', 4)



        if not isinstance(opt_offset, int) or opt_offset < 0:
            raise ArgumentError(f"'opt_offset' must be int >= 0, got {type(opt_offset)} {opt_offset}")

        if not isinstance(opt_min_days, int) or opt_min_days < 0:
            raise ArgumentError(f"'opt_min_days' must be int  >= 0, got {type(opt_min_days)} {opt_min_days}")

        if not isinstance(error_limit, int) or error_limit <= 0:
            raise ArgumentError(f"'error_limit' must be int > 0, got {type(error_limit)} {error_limit}")

        fut_offset = 0
        err_count = 0

        while True:
            try:
                # Getting future contract by offset
                fut = self.chains_futures_get(instrument, date, fut_offset)
                # Getting options chains list for the future
                opt_chain_list = self.datafeed.get_option_chains(fut)
                # Trying to find option with expiration by offset and days_to_exp > opt_min_days
                option_chain = opt_chain_list.find(date, opt_offset, min_days=opt_min_days, opt_codes=opt_codes)
                return fut, option_chain
            except ChainNotFoundError as exc:
                # Chain is not found, probably few days till expiration or no data
                err_count += 1
                # Try to seek next future contract
                fut_offset += 1
                # Taking into account options expiration that OK, but skipped by opt_offset
                opt_offset = max(opt_offset - exc.option_offset_skipped, 0)

                if err_count == error_limit:
                    # Too many errors occurred, probably no data or very strict 'opt_offset' value
                    raise ChainNotFoundError(
                        f"Couldn't find suitable chain, error limit reached. Last error: {str(exc)}. "
                        f"Try to increase 'error_limit' kwarg parameter if you are sure that data is fine.")
