from datetime import timedelta

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
from tmqr.errors import ArgumentError
from collections import OrderedDict


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
        self.instrument_info_cache = {}
        self.contract_info_cache = {}
        self.futchain_cache = {}
        self.opt_chain_cache = {}

    def get_instrument_info(self, instrument):
        """
        Returns instance of instrument AssetInfo class
        :param instrument: full qualified instrument name
        :return: AssetInfo class instance
        """
        if instrument in self.instrument_info_cache:
            # Use caching
            return self.instrument_info_cache[instrument]
        else:
            ainfo = InstrumentInfo(self.data_engine.db_get_instrument_info(instrument))
            self.instrument_info_cache[instrument] = ainfo
            return ainfo

    def get_fut_chain(self, instrument, **kwargs):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :return: FutureChain class instance
        """
        chain_dict = self.data_engine.db_get_futures_chain(instrument,
                                                           self.date_start - timedelta(days=180))

        return FutureChain([x['tckr'] for x in chain_dict],
                           asset_info=self.get_instrument_info(instrument),
                           datamanager=self.dm,
                           **kwargs)

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

        chain_list = self.data_engine.db_get_option_chains(underlying_asset.ticker)

        chain_result = self._process_raw_options_chains(chain_list, underlying_asset)

        return OptionChainList(chain_result, underlying=underlying_asset, datamanager=self.dm)

    def get_contract_info(self, tckr):
        """
        Fetch contract info for full qualified ticker name
        :param tckr: full qualified ticker
        :return: ContractInfo class instance
        """

        if tckr not in self.contract_info_cache:
            # Populate cache if contract info not set
            cinfo = ContractInfo(self.data_engine.db_get_contract_info(tckr))
            self.contract_info_cache[tckr] = cinfo

        return self.contract_info_cache[tckr]

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

        dfseries, qtype = self.data_engine.db_get_raw_series(tckr, source_type, **kwargs)

        if qtype == QTYPE_INTRADAY:
            # Convert timezone of the dataframe (in place)
            dfseries.tz_convert(tz, copy=False)

            quotes_tuple_arr = find_quotes(dfseries, dt_list)
            return [px for dt, px in quotes_tuple_arr]
        else:
            raise NotImplementedError("Quote type is not implemented yet.")
