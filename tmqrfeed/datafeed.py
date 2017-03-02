from datetime import timedelta, datetime

from tmqr.errors import ArgumentError
from tmqr.settings import *
from tmqrfeed.assetsession import AssetSession
from tmqrfeed.chains import FutureChain
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.contracts import FutureContract
from tmqrfeed.dataengines import DataEngineMongo
from tmqrfeed.instrumentinfo import InstrumentInfo


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
        # Initiating low-level data engine
        self.data_engine_settings = kwargs.get('data_engine_settings', {})
        data_engine_cls = kwargs.get('data_engine_cls', DataEngineMongo)
        self.data_engine = data_engine_cls(**self.data_engine_settings)

        # Initializing common datafeed settings
        self.date_start = kwargs.get('date_start', datetime(1900, 1, 1))

        # Cache setup
        self.instrument_info_cache = {}
        self.contract_info_cache = {}
        self.futchain_cache = {}

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
        tickers_list = [FutureContract(x['tckr'], datafeed=self) for x in chain_dict]
        return FutureChain(tickers_list,
                           self.get_instrument_info(instrument),
                           **kwargs)

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
        :param tckr:
        :param kwargs:
        :return:
        """
        date_start = kwargs.get('date_start', datetime(1900, 1, 1))
        date_end = kwargs.get('date_end', datetime(2100, 1, 1))
        tz = kwargs.get('timezone', None)
        session = kwargs.get('session', None)

        dfseries, qtype = self.data_engine.db_get_raw_series(tckr, source_type, **kwargs)

        if qtype == QTYPE_INTRADAY:
            if tz is not None:
                # Convert timezone of the dataframe (in place)
                dfseries.tz_convert(tz, copy=False)
            if session is not None:
                if isinstance(session, AssetSession):
                    # Filtering dataframe keep only requires session
                    dfseries = session.filter_dataframe(dfseries)
                elif type(session) == tuple and len(session) == 2:
                    dfseries = dfseries.between_time(start_time=session[0],
                                                     end_time=session[1],
                                                     include_start=True,
                                                     include_end=True)
                else:
                    raise ArgumentError("Session must be AssetSession or tuple of ('HH:MM', 'HH:MM')")

            return dfseries
        else:
            raise NotImplementedError("Quote type is not implemented yet.")
