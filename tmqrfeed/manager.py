from tmqr.errors import *
from tmqrfeed.contracts import ContractBase, FutureContract
from tmqrfeed.datafeed import DataFeed
from datetime import datetime
from tmqr.settings import QDATE_MIN, QDATE_MAX
from tmqrfeed.costs import Costs

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

        self.datafeed: DataFeed = feed
        """DataFeed instance for low-level data fetching"""

        # Quotes dataframe for primary series
        self._primary_quotes = None
        # Secondary dataframes dictionary for secondary series quotes
        self._secondary_quotes = {}

        # Primary series positions
        self._primary_positions = None
        # Secondary series positions dictionary
        self._secondary_positions = {}

        # Internal price cache for getting single quotes
        self._cache_single_price = {}

        self._cache_costs = {}

    def costs_set(self, market, costs):
        """
        Initiate costs settings for position PnL calculations
        :param market: market name
        :param costs: Costs class instance
        :return: 
        """
        if not isinstance(costs, Costs):
            raise ArgumentError("'costs' argument must be instance/or derived from tmqrfeed.costs.Costs class")
        self._cache_costs[market] = costs

    def costs_get(self, asset, qty):
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


    def series_primary_set(self, quote_engine_cls, *args, **kwargs):
        """
        Fetch main series used for algorithm and strategy calculations
        :param quote_engine_cls: Quote* class
        :param args: positional arguments for given Quote* class
        :param kwargs: kwargs for given Quote* class
        :return: None
        """
        if self._primary_quotes is not None:
            raise DataManagerError("series_primary_set() already called, only one instance of primary quotes allowed")

        quote_engine = quote_engine_cls(*args, **kwargs)
        self._primary_quotes, self._primary_positions = quote_engine.build()

        # Checking series validity
        self.series_check(self._primary_quotes)

    def series_extra_set(self, name, quote_engine_cls, *args, **kwargs):
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

        quote_engine = quote_engine_cls(*args, **kwargs)
        quotes, pos = quote_engine.build()

        # Checking quotes validity
        self.series_check(quotes)

        # Align and store extra series
        self._secondary_quotes[name] = self.series_align(self._primary_quotes, quotes)
        self._secondary_positions[name] = pos



    def series_align(self, primary_quotes, extra_quotes):
        # TODO: implement series alignment
        return extra_quotes

    def series_check(self, quotes):
        # TODO: implement series checks
        return True

    def series_get(self, asset: ContractBase, **kwargs):
        """
        Get asset's raw series from the DB
        :param asset: asset instance
        :param kwargs: DataFeed get_raw_series() **kwargs
        :return: series DataFrame
        """
        iinfo = asset.instrument_info
        kw_source_type = kwargs.get('source_type', asset.data_source)
        kw_timezone = kwargs.get('timezone', iinfo.timezone)
        kw_date_start = kwargs.get('date_start', QDATE_MIN)
        kw_date_end = kwargs.get('date_end', QDATE_MAX)

        return self.datafeed.get_raw_series(asset.ticker,
                                            source_type=kw_source_type,
                                            timezone=kw_timezone,
                                            date_start=kw_date_start,
                                            date_end=kw_date_end
                                            )

    def price_get(self, asset: ContractBase, date, **kwargs):
        """
        Get price at decision and execution time for given asset
        :param asset: Contract class instance
        :param date: timestamp for price
        :return: 
        """
        # Trying to search positions cache
        res = self._price_get_positions_cached(asset, date)
        if res[0] is not None:
            return res

        # Trying to search internal price cache
        res = self._price_get_cached(asset, date)
        if res[0] is not None:
            return res

        res = self._price_get_from_datafeed(asset, date, **kwargs)
        self._price_set_cached(asset, date, res)
        return res

    def _price_get_positions_cached(self, asset: ContractBase, date):

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
        :param decision_px: 
        :param exec_px: 
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
        kw_timezone = kwargs.get('timezone', iinfo.timezone)
        kw_data_options_use_prev_date = kwargs.get('data_options_use_prev_date', iinfo.data_options_use_prev_date)

        start, decision, execution, next_sess_date = iinfo.session.get(date)

        decision_px, exec_px = self.datafeed.get_raw_prices(asset.ticker,
                                                            source_type=kw_source_type,
                                                            dt_list=[decision, execution],
                                                            timezone=kw_timezone,
                                                            date_start=decision,
                                                            date_end=execution,
                                                            data_options_use_prev_date=kw_data_options_use_prev_date
                                                            )

        return decision_px, exec_px

    def chains_futures_get(self, instrument: str, date: datetime, offset: int = 0):
        """
        Get future contract from futures chains
        :param instrument: Full-qualified instrument name
        :param date: current date 
        :param offset: future expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
        :return: Future contract
        """
        fut_chain = self.datafeed.get_fut_chain(instrument)
        return fut_chain.get_contract(date, offset)

    def chains_options_get(self, instrument: str, date: datetime, **kwargs):
        """
        Find future+option chain by given criteria
        :param instrument: Full-qualified instrument name
        :param date: current date
        :param kwargs: 
            - 'opt_offset' - option expiration offset, 0 - front month, +1 - front+1, etc. (default: 0)
            - 'opt_min_days' - minimal days count until option expiration (default: 2)
            - 'error_limit' - ChainNotFoundError error limit, useful to increase when you are trying to get far 'opt_offset' (default: 4)
        :return: (tuple) FutureContract, OptionChain
        """

        opt_offset = kwargs.get('opt_offset', 0)
        opt_min_days = kwargs.get('opt_min_days', 2)
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
                option_chain = opt_chain_list.find(date, opt_offset, min_days=opt_min_days)
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
