from pymongo import MongoClient

from tmqr.settings import *

#
# Collection names constants
#
COLLECTION_ASSET_INDEX = 'asset_index'
COLLECTION_ASSET_INFO = 'asset_info'


#
# Custom exceptions classes
#
class DataEngineNotFoundError(Exception):
    pass


class DataEngineBase:
    """
    This class implements low-level interface for data fetching for different data sources
    Also this class implements AssetIndex functionality to fetch information about tickers
    """

    def __init__(self, **kwargs):
        pass


class DataEngineMongo(DataEngineBase):
    """
    This class implements low-level data fetching from MongoDB
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        mongo_host = kwargs.get('host', MONGO_CONNSTR)
        mongo_db = kwargs.get('db', MONGO_DB)

        self.client = MongoClient(mongo_host)
        self.db = self.client[mongo_db]
        self.cursors = {}

    def get_futures_chain(self, instrument, date_start=None):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :param date_start: Starting date of chain
        :return: List of futures' full-qualified ticker names
        """
        if date_start is None:
            req = {'type': 'F', 'instr': instrument}
        else:
            req = {'type': 'F', 'instr': instrument, 'exp': {'$gt': date_start}}

        return list(self.db[COLLECTION_ASSET_INDEX].find(req, projection=['tckr']).sort('exp', 1))

    def get_instrument_info(self, instrument):
        """
        Fetch asset info
        :param instrument:
        :return: asset info Mongo dict
        """
        toks = instrument.split('.')
        if len(toks) != 2:
            raise ValueError("Instrument name must be <MARKET>.<INSTRUMENT>")
        mkt_name, instr_name = toks

        ainfo_default = self.db[COLLECTION_ASSET_INFO].find_one({'instrument': '{0}.$DEFAULT$'.format(mkt_name)})
        if ainfo_default is None:
            raise DataEngineNotFoundError(
                "{0}.$DEFAULT$ record is not found in 'asset_info' collection".format(mkt_name))

        ainfo_instrument = self.db[COLLECTION_ASSET_INFO].find_one({'instrument': '{0}'.format(instrument)})

        if ainfo_instrument is not None:
            ainfo_default.update(ainfo_instrument)
        else:
            ainfo_default['instrument'] = instrument

        return ainfo_default

    def get_contract_info(self, tckr):
        """
        Fetch contract information by full qualified ticker
        :param tckr: full qualified ticker
        :return: Contract info Mongo dict
        """

        result = self.db[COLLECTION_ASSET_INDEX].find_one({'tckr': tckr})
        if result is None:
            raise DataEngineNotFoundError("Contract info for {0} not found".format(tckr))

        return result
