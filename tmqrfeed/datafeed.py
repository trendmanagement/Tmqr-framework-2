from tmqrfeed._dataengines import DataEngineMongo
from tmqrfeed.chains import FutureChain
from tmqrfeed.contracts import FutureContract


class DataFeed:
    """
    Class used to fetch data from different data sources and asset indexes
    """
    def __init__(self, preprocessorcls, postprocessors, **kwargs):
        """
        Initiate datafeed engine
        :param preprocessorcls: preprocessor class (not instance!)
        :param postprocessors: list of postprocessors
        :param kwargs:
            - 'data_engine_cls' - class of low-level data engine (default: DataEngineMongo)
            - 'data_engine_settings' - kwargs passed to low-level data engine
            - 'date_start' - starting date of all quotes requests
        """
        self.PreprocessorCls = preprocessorcls
        self.postprocessors = postprocessors

        # Initiating low-level data engine
        self.data_engine_settings = kwargs.get('data_engine_settings', {})
        DataEngineCls = kwargs.get('data_engine_cls', DataEngineMongo)
        self.data_engine = DataEngineCls(**self.data_engine_settings)

        # Initializing common datafeed settings
        self.date_start = kwargs.get('date_start', None)

    def get_fut_chain(self, instrument):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :return: FutureChain class instance
        """
        tickers_list = [x['tckr'] for x in self.data_engine.get_futures_chain(instrument, self.date_start)]
        return FutureChain(tickers_list)
