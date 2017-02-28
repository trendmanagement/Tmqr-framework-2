from datetime import timedelta, datetime

from tmqrfeed.assetinfo import AssetInfo
from tmqrfeed.chains import FutureChain
from tmqrfeed.contractinfo import ContractInfo
from tmqrfeed.dataengines import DataEngineMongo


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
        self.ainfo_cache = {}
        self.futchain_cache = {}

    def get_asset_info(self, instrument):
        """
        Returns instance of instrument AssetInfo class
        :param instrument: full qualified instrument name
        :return: AssetInfo class instance
        """
        if instrument in self.ainfo_cache:
            # Use caching
            return self.ainfo_cache[instrument]
        else:
            ainfo = AssetInfo(self.data_engine.get_asset_info(instrument))
            self.ainfo_cache[instrument] = ainfo
            return ainfo

    def get_fut_chain(self, instrument, **kwargs):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :return: FutureChain class instance
        """
        tickers_list = [x['tckr'] for x in self.data_engine.get_futures_chain(instrument,
                                                                              self.date_start - timedelta(days=180))]
        return FutureChain(tickers_list,
                           self.get_asset_info(instrument),
                           **kwargs)

    def get_contract_info(self, tckr):
        """
        Fetch contract info for full qualified ticker name
        :param tckr: full qualified ticker
        :return: ContractInfo class instance
        """
        return ContractInfo(self.data_engine.get_contract_info(tckr))
