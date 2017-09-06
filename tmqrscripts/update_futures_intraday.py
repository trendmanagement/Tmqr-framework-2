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

from datetime import time, timedelta

import pandas as pd
import pymongo
import pytz
from pymongo import MongoClient

from tmqr.settings import *

try:
    from tmqr.settings_local import *
except:
    pass

from tmqrfeed.manager import DataManager
from tmqr.serialization import *

MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmqr2?authMechanism=SCRAM-SHA-1'
MONGO_DB = 'tmqr2'

local_client = MongoClient(MONGO_CONNSTR)
local_db = local_client[MONGO_DB]

def time_to_utc(naive, timezone):
    local = pytz.timezone(timezone)
    local_dt = local.localize(naive, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt

def utc_to_time(naive, timezone):
    return naive.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone))


def import_futures_from_realtime():

    RMT_MONGO_CONNSTR = 'mongodb://tml:tml@10.0.1.2/tmldb_test?authMechanism=SCRAM-SHA-1'
    RMT_MONGO_DB = 'tmldb_test'

    remote_client = MongoClient(RMT_MONGO_CONNSTR)
    remote_db = remote_client[RMT_MONGO_DB]


    dm = DataManager()


    #chain = dm.datafeed.get_fut_chain(instrument)

    #futures = chain.get_all()

    contract_col_collection = remote_db['contractcol']
    mongo_collection = remote_db['futurebarcol']

    # Storing futures


    asset_index_collection = local_db['asset_index']

    quotes_collection = local_db['quotes_intraday']
    quotes_collection.create_index([('tckr', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)], unique=True)

    for fut in contract_col_collection.find({'_id':4718,'expirationdate':{'$gte':datetime.now()}}):  #'_id':4718,

        future_id = asset_index_collection.find_one({'extra_data.sqlid': fut['_id'], 'type': 'F'})  #fut['_id']

        if future_id != None:
            print(future_id['tckr'])

            #get latest
            #extra_data.eod_update_time

            instrument = dm.datafeed.get_instrument_info(future_id['instr'])

            if 'eod_update_time' in future_id['extra_data']:
                previous_date_time_for_realtime_query = utc_to_time(future_id['extra_data']['eod_update_time'],instrument.timezone.zone)
                previous_date_quotes_intraday_utc = future_id['extra_data']['eod_update_time']
            else:
                previous_date_time_for_realtime_query = datetime.combine(datetime.now().date() - timedelta(days=1), time(0, 0, 0))
                previous_date_quotes_intraday_utc = previous_date_time_for_realtime_query

            stored_data = quotes_collection.find_one({'dt': datetime.combine(previous_date_quotes_intraday_utc.date(), time(0, 0, 0)), 'tckr': future_id['tckr']})

            ohlc = object_load_decompress(stored_data['ohlc'])

            #print(ohlc)

            realtime_data = list(mongo_collection.find({'idcontract':fut['_id'], 'bartime':{'$gt':previous_date_time_for_realtime_query}}).sort(
                            [('datetime', 1)]))

            df = pd.DataFrame(realtime_data)
            df = df[['bartime', 'open', 'high', 'low', 'close', 'volume']]

            #print(realtime_data)

            df.rename(columns={'bartime': 'dt', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'},
                      inplace=True)
            df.set_index('dt', inplace=True)
            df.index = df.index.tz_localize(instrument.timezone).tz_convert('UTC')

            # if ohlc.empty:
            #     df_for_update = df
            # else:
            df_for_update = pd.concat([ohlc[ohlc.index < df.index[0]], df])#.reset_index(drop=True)

            #print(df_for_update)

            for idx_dt, df_value in df_for_update.groupby(by=df_for_update.index.date):
                dt = datetime.combine(idx_dt, time(0, 0, 0))
                rec = {
                    'dt': dt,
                    'tckr': future_id['tckr'],
                    'ohlc': object_save_compress(df_value)#lz4.block.compress(pickle.dumps(df_value))
                }
                quotes_collection.replace_one({'dt': dt, 'tckr': future_id['tckr']}, rec, upsert=True)

                #print('test')



    # for fut_tuple in tqdm(futures):
    #     fut = fut_tuple[0]
    #
    #     test_time = datetime.now().date() - timedelta(days=5)
    #
    #     if all_contracts or fut_tuple[2] >= test_time:
    #
    #         if all_contracts:
    #             data = list(mongo_collection.find({'idcontract': fut.contract_info.extra('sqlid')}).sort([('datetime', 1)]))
    #         else:
    #
    #             if fut.contract_info.extra('eod_update_time') != None:
    #                 data = list(
    #                     mongo_collection.find({'idcontract': fut.contract_info.extra('sqlid'),
    #                         'datetime': {'$gte': datetime.combine(
    #                             time_to_utc(fut.contract_info.extra('eod_update_time'),fut.instrument_info.timezone.zone).date(), time(0, 0, 0))}}).sort(
    #                         [('datetime', 1)]))
    #             else:
    #                 data = list(
    #                     mongo_collection.find({'idcontract': fut.contract_info.extra('sqlid'),
    #                                            'datetime': {'$gte': datetime.combine(test_time, time(0, 0, 0))}}).sort(
    #                         [('datetime', 1)]))
    #
    #         if len(data) == 0:
    #             print("Empty contract series for {0} ... skipping".format(fut))
    #             continue
    #         df = pd.DataFrame(data)
    #         df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
    #         df.rename(columns={'datetime': 'dt', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'},
    #                   inplace=True)
    #         df.set_index('dt', inplace=True)
    #         df.index = df.index.tz_localize(fut.instrument_info.timezone).tz_convert('UTC')
    #
    #         for idx_dt, df_value in df.groupby(by=df.index.date):
    #             dt = datetime.combine(idx_dt, time(0, 0, 0))
    #             rec = {
    #                 'dt': dt,
    #                 'tckr': fut.ticker,
    #                 'ohlc': lz4.block.compress(pickle.dumps(df_value))
    #             }
    #             quotes_collection.replace_one({'dt': dt, 'tckr': fut.ticker}, rec, upsert=True)
    #
    #         datetime(data[-1]['datetime']).date()
    #
    #         asset_index_collection.update_one({'tckr': fut.ticker}, {'$set':{'extra_data.eod_update_time':df.iloc[-1].name}})

import_futures_from_realtime()
