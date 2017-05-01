import numpy as np
import pytz
import pyximport

from tmqr.settings import *
from tmqrfeed.chains import FutureChain, OptionChainList
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.contracts import ContractBase, OptionContract
from tmqrfeed.dataengines import DataEngineMongo
from tmqrfeed.instrumentinfo import InstrumentInfo

pyximport.install(setup_args={"include_dirs": np.get_include()})
from tmqrfeed.fast_data_handling import find_quotes
from tmqr.errors import ArgumentError, OptionsEODQuotesNotFoundError, ChainNotFoundError
from collections import OrderedDict
from datetime import datetime, time, timedelta


class DataFeed:
    """
    Class used to fetch data from different data sources and asset indexes
    """

    def __init__(self, **kwargs):
        """
        Initiate datafeed engine
        :param kwargs:
            - 'data_engine_cls' - class of low-level data engine (default: DataEngineMongo)
            - 'data_engine_settings' - kwargs passed to low-level data engine
            - 'date_start' - starting date of all quotes requests
        """
        self.dm = kwargs.get('datamanager', None)
        # Initiating low-level data engine
        self.data_engine_settings = kwargs.get('data_engine_settings', {})
        data_engine_cls = kwargs.get('data_engine_cls', DataEngineMongo)
        self.data_engine = data_engine_cls(**self.data_engine_settings)

        # Initializing common datafeed settings
        self.date_start = kwargs.get('date_start', QDATE_MIN)

        # Cache setup
        self._cache_instrument_info = {}
        self._cache_contract_info = {}
        self._cache_futchain = {}
        self._cache_opt_chain = {}
        self._cache_price_data = {}

    def get_instrument_info(self, instrument):
        """
        Returns instance of instrument AssetInfo class
        :param instrument: full qualified instrument name
        :return: AssetInfo class instance
        """
        if instrument in self._cache_instrument_info:
            # Use caching
            return self._cache_instrument_info[instrument]
        else:
            ainfo = InstrumentInfo(self.data_engine.db_get_instrument_info(instrument))
            self._cache_instrument_info[instrument] = ainfo
            return ainfo

    def get_fut_chain(self, instrument, **kwargs):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :return: FutureChain class instance
        """
        if instrument not in self._cache_futchain:
            chain_dict = self.data_engine.db_get_futures_chain(instrument, self.date_start - timedelta(days=180))
            asset_info = self.get_instrument_info(instrument)

            default_fut_months = asset_info.futures_months
            rollover_days_before = kwargs.pop('rollover_days_before', asset_info.rollover_days_before)
            futures_months = kwargs.pop('futures_months', default_fut_months)
            fut_chain = FutureChain([x['tckr'] for x in chain_dict],
                                    datamanager=self.dm,
                                    rollover_days_before=rollover_days_before,
                                    futures_months=futures_months,
                                    **kwargs)
            self._cache_futchain[instrument] = fut_chain

        return self._cache_futchain[instrument]

    def _process_raw_options_chains(self, chain_list, underlying_asset: ContractBase):
        """
        Converting MongoDB option chains to OptionsChainList friendly format
        :param chain_list: result of data_engine.db_get_option_chains()
        :param underlying_asset: underlying asset instance
        :return: OrderedDict[ expiration, OrderedDict[strike, CallPutTickers] ]
        """
        chain_result = OrderedDict()
        for exp in chain_list:
            options = chain_result.setdefault(exp['_id']['date'], OrderedDict())

            chain = exp['chain']
            for i, strike_rec in enumerate(chain):
                strike = strike_rec['strike']
                if i == 0:
                    continue

                if strike == chain[i - 1]['strike']:
                    # We have put call pair
                    if strike_rec['type'] == 'C':
                        call_idx = i
                        put_idx = i - 1
                    else:
                        call_idx = i - 1
                        put_idx = i

                    options[strike] = (
                        OptionContract(chain[call_idx]['tckr'], datamanager=self.dm, underlying=underlying_asset),
                        OptionContract(chain[put_idx]['tckr'], datamanager=self.dm, underlying=underlying_asset)
                    )
        return chain_result

    def get_option_chains(self, underlying_asset: ContractBase):
        """
        Fetch OptionChain object for particular underlying ticker
        :param underlying_asset: underlying contract instance
        :return: OptionChainList object
        """
        if underlying_asset not in self._cache_opt_chain:
            chain_list = self.data_engine.db_get_option_chains(underlying_asset.ticker)
            if len(chain_list) == 0:
                raise ChainNotFoundError(f"Couldn't find options chains in DB for {underlying_asset}")
            chain_result = self._process_raw_options_chains(chain_list, underlying_asset)

            opt_chain = OptionChainList(chain_result, underlying=underlying_asset, datamanager=self.dm)
            self._cache_opt_chain[underlying_asset] = opt_chain

        return self._cache_opt_chain[underlying_asset]

    def get_contract_info(self, tckr):
        """
        Fetch contract info for full qualified ticker name
        :param tckr: full qualified ticker
        :return: ContractInfo class instance
        """

        if tckr not in self._cache_contract_info:
            # Populate cache if contract info not set
            cinfo = ContractInfo(self.data_engine.db_get_contract_info(tckr))
            self._cache_contract_info[tckr] = cinfo

        return self._cache_contract_info[tckr]

    def get_raw_series(self, tckr, source_type, **kwargs):
        """
        Fetch raw series for asset from the datasource
        :param tckr: full qualified ticker
        :param source_type: datasource type
        :param kwargs:
            - 'timezone' - pytz.timezone instance or (str) pytz timezone name
            - Also dataengine.db_get_raw_series() **kwargs
        :return:
        """
        tz = kwargs.get('timezone', None)
        if type(tz) == str:
            tz = pytz.timezone(tz)

        dfseries, qtype = self.data_engine.db_get_raw_series(tckr, source_type, **kwargs)

        if qtype == QTYPE_INTRADAY:
            if tz is not None:
                # Convert timezone of the dataframe (in place)
                dfseries.tz_convert(tz, copy=False)
            return dfseries
        else:
            raise NotImplementedError("Quote type is not implemented yet.")

    def get_raw_prices(self, tckr, source_type, dt_list, **kwargs):
        tz = kwargs.get('timezone', None)
        if tz is None:
            raise ArgumentError("'timezone' kwarg must be set")

        if type(tz) == str:
            tz = pytz.timezone(tz)
        # Trying to get cache
        dfseries, qtype = self._cache_price_data.get(tckr, (None, None))
        if dfseries is None:
            # Cache is not exists for 'tckr'
            dfseries, qtype = self.data_engine.db_get_raw_series(tckr, source_type, **kwargs)

        if qtype == QTYPE_INTRADAY:
            # Convert timezone of the dataframe (in place)
            dfseries.tz_convert(tz, copy=False)
            quotes_tuple_arr = find_quotes(dfseries, dt_list)
            return [px for dt, px in quotes_tuple_arr]

        elif qtype == QTYPE_OPTIONS_EOD:
            # IMPORTANT: make sure that caching raw data (before shifting, and changing)
            # And don't changing cached values
            self._cache_price_data[tckr] = (dfseries, qtype)

            data_options_use_prev_date = kwargs.get('data_options_use_prev_date', False)
            df = dfseries['data']
            if data_options_use_prev_date:
                df = df.shift(1)

            try:
                return [df.at[datetime.combine(d.date(), time(23, 59, 59)), 'iv'] for d in dt_list]
            except KeyError:
                raise OptionsEODQuotesNotFoundError(f"Option {tckr} EOD quotes not found at {dt_list}")
        else:
            raise NotImplementedError("Quote type is not implemented yet.")
