'''
Options data updates script
This script should be scheduled on daily basis after span data was loaded.  Note that in options collection the quotes data is stored per ticker basis. So to maintain the DB in the granular you have to re-upload all non-expired contracts each day.
Note that all data is a Pandas.DataFrame with the index where dates are time-zone aware and in format YYYY-MM-DD 23:59:59
Here is a sample upload script: https://10.0.1.2:8889/notebooks/data/Import%20options%20data.ipynb
To update you have 2 options (I don’t know which is the best, you should probably do some benchmarks):
1. Read the option data record from new DB, decompress the binary data to the Pandas.DataFrame and update the Pandas.DataFrame, then save the data.
2. Read all options quotes for the contract in the old DB, parse these quotes to the Pandas.DataFrame and save.
'''

import pickle
from datetime import time

import lz4
import pandas as pd
import pytz
from pymongo import MongoClient
from tmqr.settings import *
from tqdm import tqdm
from tradingcore.messages import *
from tradingcore.signalapp import SignalApp, APPCLASS_DATA

local_client = MongoClient(MONGO_CONNSTR)
local_db = local_client[MONGO_DB]


RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
RMT_MONGO_DB = 'tmldb_v2'

remote_client = MongoClient(RMT_MONGO_CONNSTR)
remote_db = remote_client[RMT_MONGO_DB]

signalapp = SignalApp('V2 calcs', APPCLASS_DATA, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)

def import_ticker(tckr, sqlid):
    quotes_list = []
    for rec in remote_db['options_data'].find({'idoption': sqlid}).sort([('datetime', 1)]):
        """
        {
        "_id" : ObjectId("58c39fd334ac22701940ed0c"),
        "price" : 8.12,
        "datetime" : ISODate("2011-01-03T00:00:00.000Z"),
        "timetoexpinyears" : 0.94794,
        "impliedvol" : 0.275,
        "idoption" : 32110
        }
        """
        qdict = {
            'dt': pytz.utc.localize(datetime.combine(rec['datetime'].date(), time(23, 59, 59))),
            'px': rec['price'],
            'toexp': rec['timetoexpinyears'],
            'iv': rec['impliedvol']
        }
        quotes_list.append(qdict)

    if len(quotes_list) == 0:
        return

    qdf = pd.DataFrame(quotes_list).set_index('dt')
    local_db['quotes_options_eod'].replace_one({'_id': tckr},
                                               {'_id': tckr,
                                                'data': lz4.block.compress(pickle.dumps(qdf)),
                                                },
                                               upsert=True
                                               )

def import_options(INSTRUMENT, exp_after_current_day = False):
    # for row in local_db['asset_info'].find({}):
        # INSTRUMENT = row['instrument']

        #INSTRUMENT = "US.6C"

    expirations = []

    if not exp_after_current_day:
        cursor = local_db['asset_index'].aggregate([
                    {'$match': {
                        'instr': INSTRUMENT,
                        'type': {'$in': ['P', 'C']},
                    }},
                    {'$sort': {'strike': 1}},
                    {'$project': {'tckr': 1, 'exp': 1, 'strike': 1, 'type': 1}},
                    {'$group': {
                        '_id': {'date': '$exp'},
                        #'chain': {'$push': '$exp'},
                    }
                    },
                    {'$sort': {"_id.date": 1}}
                ])

    else:
        cursor = local_db['asset_index'].aggregate([
                    {'$match': {
                        'instr': INSTRUMENT,
                        'type': {'$in': ['P', 'C']},
                        'exp': {'$gte':datetime.combine(datetime.now().date(), time(0, 0, 0))}
                    }},
                    {'$sort': {'strike': 1}},
                    {'$project': {'tckr': 1, 'exp': 1, 'strike': 1, 'type': 1}},
                    {'$group': {
                        '_id': {'date': '$exp'},
                        # 'chain': {'$push': '$exp'},
                    }
                    },
                    {'$sort': {"_id.date": 1}}
                ])

    for x in cursor:
        expirations.append(x['_id']['date'])

    #expirations

    tickers_data = {}

    tickers_col = local_db['asset_index'].find({'instr': INSTRUMENT,
                                                'type': {'$in': ['P','C']},
                                                'exp': {'$in': expirations}})
    for tdata in tickers_col:
        tickers_data[tdata['tckr']] = tdata['extra_data']['sqlid']

    len(tickers_data)

    #tckr = 'US.C.F-CL-F12-111221.111215@100.0'
    #sqlid = 32110.0

    for tckr, sqlid in tqdm(tickers_data.items()):
        import_ticker(tckr, sqlid)


    signalapp.send(MsgStatus('V2_Option_Span_update', 'V2 Option Data finished {0}'.format(INSTRUMENT), notify=True))

def run_full_options():
    for row in local_db['asset_info'].find({}):
        import_options(row['instrument'], exp_after_current_day=False)

def run_full_options_selected_instrument(instrument):
    import_options(instrument, exp_after_current_day=False)


def run_current_options():
    for row in local_db['asset_info'].find({}):
        import_options(row['instrument'], exp_after_current_day=True)

def run_current_options_selected_instrument(instrument):
    import_options(instrument, exp_after_current_day=True)
