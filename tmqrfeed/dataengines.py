import pickle

import pandas as pd
from pymongo import MongoClient

from tmqr.errors import *
from tmqr.settings import *

#
# Collection names constants
#
COLLECTION_ASSET_INDEX = 'asset_index'
COLLECTION_ASSET_INFO = 'asset_info'


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

    def db_get_futures_chain(self, instrument, date_start=None):
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

    def db_get_instrument_info(self, instrument):
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

    def db_get_contract_info(self, tckr):
        """
        Fetch contract information by full qualified ticker
        :param tckr: full qualified ticker
        :return: Contract info Mongo dict
        """

        result = self.db[COLLECTION_ASSET_INDEX].find_one({'tckr': tckr})
        if result is None:
            raise DataEngineNotFoundError("Contract info for {0} not found".format(tckr))

        return result

    def db_get_raw_series(self, tckr, source_type, **kwargs):
        if source_type == SRC_INTRADAY:
            return self._source_intraday_get_series(tckr, **kwargs)
        else:
            raise DataSourceNotFoundError("Unknown 'datasource' type")

    def _source_intraday_get_series(self, tckr, **kwargs):
        """
        Returns raw series dataframe from intraday mongo data base
        :param tckr: full qualified ticker name
        :param kwargs: db_get_raw_series kwargs
        :return: pandas DataFrame
        """
        date_start = kwargs.get('date_start', None)
        date_end = kwargs.get('date_end', None)

        dt_filter = {}
        if date_start is not None:
            dt_filter['$gte'] = date_start
        if date_end is not None:
            dt_filter['$lte'] = date_end

        request = {'tckr': tckr}
        if len(dt_filter) > 0:
            request['dt'] = dt_filter

        dframes_list = []
        for data in self.db[SRC_INTRADAY].find(request):
            df = pickle.loads(data['ohlc'])
            dframes_list.append(df)

        if len(dframes_list) == 0:
            raise IntradayQuotesNotFoundError("No data found for {0}".format(tckr))

        return pd.concat(dframes_list), QTYPE_INTRADAY
