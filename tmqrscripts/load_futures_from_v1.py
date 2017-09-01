'''
Futures data updates script
Futures data is a most important and most complex in terms of storage.  The data is stored one record per day:
{
    "_id" : ObjectId("59119f38ca95a69e1bb7c1b3"),
    "dt" : ISODate("2011-02-11T00:00:00.000Z"),
    "tckr" : "US.F.ES.H11.110318",
    "ohlc" : { "$binary" : <a lot of bytes> "$type" : "00" }
}
Where ‘ohlc’ is a compressed and pickled Pandas.DataFrame of minutes bars. The dataframe’s index is in datatime format of UTC timezone this is very important. You can add all bars of trading session, the trading session filtering is applied later by framework’s code. Also keep in mind  that all data should be clean, you have to apply data filtering before you add quotes to the dataframe.
Probably it’s better to build online updater script for old DB[‘tmldb_test’][‘futurebarcol’] which will cache daily data and write it when new bar is arrived.
'''

import sys, argparse, logging
from datetime import datetime, time, timedelta
from decimal import Decimal
import pymongo
from pymongo import MongoClient
from tqdm import tqdm, tnrange, tqdm_notebook
import pandas as pd
from tmqr.settings import *
import pickle
import lz4
try:
    from tmqr.settings_local import *
except:
    pass

from tmqrfeed.manager import DataManager

MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmqr2?authMechanism=SCRAM-SHA-1'
MONGO_DB = 'tmqr2'

local_client = MongoClient(MONGO_CONNSTR)
local_db = local_client[MONGO_DB]

def import_futures_from_v1(instrument, all_contracts = True):

    RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
    RMT_MONGO_DB = 'tmldb_v2'

    remomote_client = MongoClient(RMT_MONGO_CONNSTR)
    remote_db = remomote_client[RMT_MONGO_DB]


    dm = DataManager()


    chain = dm.datafeed.get_fut_chain(instrument)

    futures = chain.get_all()

    # Storing futures
    mongo_collection = remote_db['contracts_bars']


    quotes_collection = local_db['quotes_intraday']
    quotes_collection.create_index([('tckr', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)], unique=True)

    for fut_tuple in tqdm(futures):
        fut = fut_tuple[0]

        if all_contracts or fut_tuple[2] >= datetime.now().date() - timedelta(days=5):

            data = list(mongo_collection.find({'idcontract': fut.contract_info.extra('sqlid')}).sort([('datetime', 1)]))
            if len(data) == 0:
                print("Empty contract series for {0} ... skipping".format(fut))
                continue
            df = pd.DataFrame(data)
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
            df.rename(columns={'datetime': 'dt', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'},
                      inplace=True)
            df.set_index('dt', inplace=True)
            df.index = df.index.tz_localize(fut.instrument_info.timezone).tz_convert('UTC')

            for idx_dt, df_value in df.groupby(by=df.index.date):
                dt = datetime.combine(idx_dt, time(0, 0, 0))
                rec = {
                    'dt': dt,
                    'tckr': fut.ticker,
                    'ohlc': lz4.block.compress(pickle.dumps(df_value))
                }
                quotes_collection.replace_one({'dt': dt, 'tckr': fut.ticker}, rec, upsert=True)


def run_all_futures():

    asset_info_collection = local_db['asset_info']

    for instrument in asset_info_collection.find({}):

        if not 'DEFAULT' in instrument['instrument']:

            import_futures_from_v1(instrument['instrument'], all_contracts = True)


def run_current_futures():

    asset_info_collection = local_db['asset_info']

    for instrument in asset_info_collection.find({}):

        if not 'DEFAULT' in instrument['instrument']:

            import_futures_from_v1(instrument['instrument'], all_contracts=False)
