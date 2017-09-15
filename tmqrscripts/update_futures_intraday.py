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
from tmqr.serialization import *

from tmqrfeed.manager import DataManager

from tqdm import tqdm


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

def fill_framework2_db(data, future_id, instrument, quotes_intraday_collection_v2):

    if len(data) == 0:
        print("Empty historical contract series for {0} ... skipping".format(future_id['tckr']))
        return None
    else:
        df = pd.DataFrame(data)
        df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']]
        df.rename(columns={'datetime': 'dt', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c',
                           'volume': 'v'},
                  inplace=True)
        df.set_index('dt', inplace=True)
        df.index = df.index.tz_localize(instrument.timezone).tz_convert('UTC')

        for idx_dt, df_value in df.groupby(by=df.index.date):
            dt = datetime.combine(idx_dt, time(0, 0, 0))
            rec = {
                'dt': dt,
                'tckr': future_id['tckr'],
                'ohlc': object_save_compress(df_value)  # lz4.block.compress(pickle.dumps(df_value))
            }
            quotes_intraday_collection_v2.replace_one({'dt': dt, 'tckr': future_id['tckr']}, rec, upsert=True)

        #asset_index_collection_v2.update_one({'tckr': future_id['tckr']},
        #                                  {'$set': {'extra_data.eod_update_time': df.iloc[-1].name}})

        return df.iloc[-1].name

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

    asset_info_collection_v2 = local_db['asset_info']
    asset_index_collection_v2 = local_db['asset_index']
    #asset_index_collection_v2.create_index([('extra_data.sqlid', pymongo.ASCENDING), ('type', pymongo.ASCENDING)], unique=False)

    quotes_intraday_collection_v2 = local_db['quotes_intraday']
    quotes_intraday_collection_v2.create_index([('tckr', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)], unique=True)

    #for fut in tqdm(contract_col_collection.find({'expirationdate':{'$gte':datetime.now()}})):  #'_id':4718,

    realtime_contract_id_list = list(
        contract_col_collection.find({'expirationdate': {'$gte': datetime.now()}}, {'_id': 1}))
    realtime_contract_id_df = pd.DataFrame(realtime_contract_id_list)
    realtime_contract_id_df.set_index('_id', inplace=True)

    for instrument in asset_info_collection_v2.find({}):

        if not 'DEFAULT' in instrument['instrument']:


            #chain = dm.datafeed.get_fut_chain(instrument['instrument'], date_start=datetime.now().date())
            #futures = chain.get_all()

            for future_id in tqdm(asset_index_collection_v2.find({'$and':[{'exp':{'$gte':datetime.now()}},
                                                                      {'exp':{'$lte': datetime.now() + timedelta(days=365)}}],
                                                               'type': 'F',
                                                               'instr':instrument['instrument']})): #fut['_id']

                if future_id['extra_data']['sqlid'] in realtime_contract_id_df.index:
                    #print(future_id['tckr'])

                    #get latest
                    #extra_data.eod_update_time

                    instrument = dm.datafeed.get_instrument_info(future_id['instr'])

                    stored_data = list(quotes_intraday_collection_v2.find(
                        {'tckr': future_id['tckr']}).sort([('dt', -1)]).limit(1))

                    if len(stored_data) == 0:


                    #if not 'eod_update_time' in future_id['extra_data']:
                        '''this is where the future is updated from the historical contracts_bars'''

                        data = list(mongo_collection.find({'idcontract': future_id['extra_data']['sqlid']}).sort(
                            [('datetime', 1)]))


                        previous_date_quotes_intraday_utc = fill_framework2_db(data, future_id, instrument, quotes_intraday_collection_v2,)

                    else:
                        '''below checks the last date of update and if falls outside the acceptable update days will pull data from the historical list of bars'''
                        ohlc = object_load_decompress(stored_data[0]['ohlc'])

                        previous_date_quotes_intraday_utc = ohlc.index[-1]

                        previous_date_time_in_local_timezone = utc_to_time(previous_date_quotes_intraday_utc,
                                                                            instrument.timezone.zone)

                        #python weekdays 0 Mon, 6 Sun
                        acceptable_offset = 1
                        if datetime.today().weekday() == 0:
                            acceptable_offset = 3

                        if datetime.today().replace(tzinfo=instrument.timezone) - previous_date_time_in_local_timezone > timedelta(days=acceptable_offset):
                            data = list(
                                mongo_collection.find({'idcontract': future_id['extra_data']['sqlid'],
                                                       'datetime': {'$gt': previous_date_time_in_local_timezone}}).sort(
                                    [('datetime', 1)]))

                            previous_date_quotes_intraday_utc = fill_framework2_db(data, future_id, instrument, quotes_intraday_collection_v2)


                    if previous_date_quotes_intraday_utc != None:

                        previous_date_time_in_local_timezone = utc_to_time(previous_date_quotes_intraday_utc,
                                                                           instrument.timezone.zone)




                        #previous_date_time_for_realtime_query = datetime.combine(datetime.now().date() - timedelta(days=1), time(0, 0, 0))
                        #previous_date_quotes_intraday_utc = previous_date_time_for_realtime_query


                    #if 'eod_update_time' in future_id['extra_data']:
                    #    previous_date_time_for_realtime_query = utc_to_time(future_id['extra_data']['eod_update_time'],instrument.timezone.zone)
                    #    previous_date_quotes_intraday_utc = future_id['extra_data']['eod_update_time']
                    else:

                        previous_date_time_in_local_timezone = datetime.combine(datetime.now().date() - timedelta(days=1), time(0, 0, 0))
                        previous_date_quotes_intraday_utc = time_to_utc(previous_date_time_in_local_timezone, instrument.timezone.zone)

                    stored_data = quotes_intraday_collection_v2.find_one({'dt': datetime.combine(previous_date_quotes_intraday_utc.date(), time(0, 0, 0)), 'tckr': future_id['tckr']})

                    if stored_data == None:
                        ohlc = pd.DataFrame()
                    else:
                        ohlc = object_load_decompress(stored_data['ohlc'])

                    #print(ohlc)

                    realtime_data = list(mongo_collection.find({'idcontract':future_id['extra_data']['sqlid'], 'bartime':{'$gte':previous_date_time_in_local_timezone}}).sort(
                                    [('datetime', 1)]))

                    realtime_df = pd.DataFrame(realtime_data)

                    if not realtime_df.empty:
                        realtime_df = realtime_df[['bartime', 'open', 'high', 'low', 'close', 'volume']]

                        #print(realtime_data)

                        realtime_df.rename(columns={'bartime': 'dt', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'volume': 'v'},
                                  inplace=True)
                        realtime_df.set_index('dt', inplace=True)
                        realtime_df.index = realtime_df.index.tz_localize(instrument.timezone).tz_convert('UTC')

                        if ohlc.empty:
                            df_for_update = realtime_df
                        else:
                            df_for_update = pd.concat([ohlc[ohlc.index < realtime_df.index[0]], realtime_df])#.reset_index(drop=True)

                        #print(df_for_update)

                        for idx_dt, df_value in df_for_update.groupby(by=df_for_update.index.date):
                            dt = datetime.combine(idx_dt, time(0, 0, 0))
                            rec = {
                                'dt': dt,
                                'tckr': future_id['tckr'],
                                'ohlc': object_save_compress(df_value)#lz4.block.compress(pickle.dumps(df_value))
                            }
                            quotes_intraday_collection_v2.replace_one({'dt': dt, 'tckr': future_id['tckr']}, rec, upsert=True)

                            #print('test')

                        #asset_index_collection_v2.update_one({'tckr': future_id['tckr']},{'$set': {'extra_data.eod_update_time': df_for_update.iloc[-1].name}})


import_futures_from_realtime()
