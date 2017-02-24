import pickle
from tmqr.settings import *
from pymongo import MongoClient
from datetime import datetime


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

    def get_futures_chain(self, instrument, start_date=None):
        """
        Fetch futures chain for particular instrument
        :param instrument: Full-qualified instrument name <Market>.<Name>
        :param start_date: Starting date of chain
        :return: List of futures' full-qualified ticker names
        """
        if start_date is None:
            req = {'type': 'F', 'instr': instrument}
        else:
            req = {'type': 'F', 'instr': instrument, 'exp': {'$gt': start_date}}

        return list(self.db['asset_index'].find(req, projection=['tckr']).sort('exp', 1))
