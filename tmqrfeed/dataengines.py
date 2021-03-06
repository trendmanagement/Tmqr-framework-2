import pickle


import pandas as pd
from pymongo import MongoClient
import pymongo

from tmqr.errors import *
from tmqr.settings import *
from datetime import date, datetime, time
from tmqr.serialization import object_load_decompress
#
# Collection names constants
#
COLLECTION_ASSET_INDEX = 'asset_index'
COLLECTION_ASSET_INFO = 'asset_info'
COLLECTION_INDEX_DATA = 'index_data'
COLLECTION_ALPHA_DATA = 'alpha_data'
COLLECTION_RFR = 'quotes_riskfreerate'


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

    def db_get_option_chains(self, underlying_tckr):
        """
        Fetch options chains (all expirations and strikes) for given underlying_tckr
        :param underlying_tckr: option's underlying contract tckr code (for example: future tckr code)
        :return: list of options aggregated chains
        """
        cursor = self.db[COLLECTION_ASSET_INDEX].aggregate([
            {'$match': {
                'underlying': underlying_tckr,
                'type': {'$in': ['P', 'C']},
            }},
            {'$sort': {'strike': 1}},
            {'$project': {'tckr': 1, 'exp': 1, 'strike': 1, 'type': 1}},
            {'$group': {
                '_id': {'date': '$exp'},
                'chain': {'$push': '$$ROOT'},
            }
            },
            {'$sort': {"_id.date": 1}}
        ])
        return list(cursor)

    def db_get_instrument_info(self, instrument):
        """
        Fetch asset info
        :param instrument:
        :return: asset info Mongo dict
        """
        toks = instrument.split('.')
        if len(toks) != 2:
            raise ArgumentError("Instrument name must be <MARKET>.<INSTRUMENT>")
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

    def db_get_last_quote_date(self, tckr, source_type, **kwargs):
        if source_type == SRC_INTRADAY:
            return self._source_intraday_get_last_quote(tckr, **kwargs)
        if source_type == SRC_OPTIONS_EOD:
            return self._source_options_eod_get_last_quote(tckr, **kwargs)
        raise DataSourceNotFoundError("Unknown 'datasource' type")

    def _source_intraday_get_last_quote(self, tckr, **kwargs):
        """
        Returns raw series dataframe from intraday mongo data base
        :param tckr: full qualified ticker name
        :param kwargs: db_get_raw_series kwargs
        :return: (tuple) pandas DataFrame, QTYPE
        """
        for data in self.db[SRC_INTRADAY].find({'tckr': tckr}).sort([('dt', -1)]).limit(1):
            df = object_load_decompress(data['ohlc'])
            if not isinstance(df, pd.DataFrame):
                raise DBDataCorruptionError(
                    f"{tckr} data is corrupted in {SRC_INTRADAY} collection at {data['dt']}, "
                    f"expected pd.DataFrame, got {type(data['ohlc'])}")

            if len(df) == 0:
                raise IntradayQuotesNotFoundError(f"Empty data record for {tckr} ")

            return df.index[-1]

        raise IntradayQuotesNotFoundError(f"No data found for {tckr}")

    def _source_options_eod_get_last_quote(self, tckr, **kwargs):
        data = self.db[SRC_OPTIONS_EOD].find_one({'_id': tckr})
        if data is None:
            raise OptionsEODQuotesNotFoundError(f"No data found for {tckr} in options EOD database")

        data['data'] = object_load_decompress(data['data'])

        if not isinstance(data['data'], pd.DataFrame):
            raise DBDataCorruptionError(
                f"{tckr} data is corrupted in {SRC_OPTIONS_EOD} collection, expected pd.DataFrame, got {type(data['data'])}")

        if len(data['data']) == 0:
            raise OptionsEODQuotesNotFoundError(f"No data found for {tckr} in options EOD database")

        return data['data'].index[-1]


    def db_get_raw_series(self, tckr, source_type, **kwargs):
        if source_type == SRC_INTRADAY:
            return self._source_intraday_get_series(tckr, **kwargs)
        if source_type == SRC_OPTIONS_EOD:
            return self._source_options_eod_get_series(tckr, **kwargs)

        raise DataSourceNotFoundError("Unknown 'datasource' type")

    def _source_intraday_get_series(self, tckr, **kwargs):
        """
        Returns raw series dataframe from intraday mongo data base
        :param tckr: full qualified ticker name
        :param kwargs: db_get_raw_series kwargs
        :return: (tuple) pandas DataFrame, QTYPE
        """
        date_start = kwargs.get('date_start', None)
        date_end = kwargs.get('date_end', None)

        dt_filter = {}
        if date_start is not None:
            dt_filter['$gte'] = datetime.combine(date_start, time(0, 0, 0))
        if date_end is not None:
            dt_filter['$lte'] = datetime.combine(date_end, time(0, 0, 0))

        request = {'tckr': tckr}
        if len(dt_filter) > 0:
            request['dt'] = dt_filter

        dframes_list = []
        for data in self.db[SRC_INTRADAY].find(request):
            df = object_load_decompress(data['ohlc'])
            if not isinstance(df, pd.DataFrame):
                raise DBDataCorruptionError(
                    f"{tckr} data is corrupted in {SRC_INTRADAY} collection at {data['dt']}, "
                    f"expected pd.DataFrame, got {type(data['ohlc'])}")

            dframes_list.append(df)

        if len(dframes_list) == 0:
            raise IntradayQuotesNotFoundError(f"No data found for {tckr} in period {date_start}-{date_end}")

        return pd.concat(dframes_list), QTYPE_INTRADAY

    def _source_options_eod_get_series(self, tckr, **kwargs):
        data = self.db[SRC_OPTIONS_EOD].find_one({'_id': tckr})
        if data is None:
            raise OptionsEODQuotesNotFoundError(f"No data found for {tckr} in options EOD database")

        data['data'] = object_load_decompress(data['data'])

        if not isinstance(data['data'], pd.DataFrame):
            raise DBDataCorruptionError(
                f"{tckr} data is corrupted in {SRC_OPTIONS_EOD} collection, expected pd.DataFrame, got {type(data['data'])}")

        return data['data'], QTYPE_OPTIONS_EOD

    def db_save_index(self, index_data):
        """
        Saves index data to the MongoDB
        :param index_data: serialized index dictionary see. IndexBase.serialize()
        :return: 
        """
        self.db[COLLECTION_INDEX_DATA].create_index([('name', pymongo.ASCENDING)])
        self.db[COLLECTION_INDEX_DATA].replace_one({'name': index_data['name']}, index_data, upsert=True)

    def db_load_index(self, index_name):
        """
        Loads index data from the MongoDB
        :param index_name:
        :return:
        """
        idx = self.db[COLLECTION_INDEX_DATA].find_one({'name': index_name})
        if idx is None:
            raise DataEngineNotFoundError(f"Index '{index_name}' is not found in the DB")
        return idx

    def db_save_alpha(self, alpha_data):
        """
        Saves index data to the MongoDB
        :param alpha_data: serialized alpha dictionary see. StrategyBase.serialize()
        :return:
        """
        self.db[COLLECTION_ALPHA_DATA].create_index([('name', pymongo.ASCENDING)])
        self.db[COLLECTION_ALPHA_DATA].replace_one({'name': alpha_data['name'].replace('.', '_')}, alpha_data, upsert=True)

    def db_load_alpha(self, alpha_name):
        """
        Loads index data from the MongoDB
        :param alpha_name:
        :return:
        """
        idx = self.db[COLLECTION_ALPHA_DATA].find_one({'name': alpha_name.replace('.', '_')})
        if idx is None:
            raise DataEngineNotFoundError(f"Alpha '{alpha_name}' is not found in the DB")
        return idx

    def db_get_rfr_series(self, market):
        """
        Returns risk free rate series for specific market
        :param market: market name
        :return: Pandas.Series
        """
        rfr = self.db[COLLECTION_RFR].find_one({'market': market})
        if rfr is None:
            raise DataEngineNotFoundError(f"RiskFreeRate series is not found in the DB for the '{market}' market")
        return object_load_decompress(rfr['rfr_series'])



