'''
Risk free-rate update script
RFR series also should be loaded and updated at daily basis. 
Here is full functional notebook: https://10.0.1.2:8889/notebooks/data/Import%20risk%20free%20rate%20data.ipynb
'''

import sys, argparse, logging
from datetime import datetime, time
from decimal import Decimal
import pymongo
from pymongo import MongoClient
from tqdm import tqdm, tnrange, tqdm_notebook
import pandas as pd
from tmqr.settings import *
import pickle
import lz4

from tmqrfeed.manager import DataManager


RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
RMT_MONGO_DB = 'tmldb_v2'

remomote_client = MongoClient(RMT_MONGO_CONNSTR)
remote_db = remomote_client[RMT_MONGO_DB]

MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmqr2?authMechanism=SCRAM-SHA-1'
#MONGO_CONNSTR = 'mongodb://localhost'
MONGO_DB = 'tmqr2'

local_client = MongoClient(MONGO_CONNSTR)
local_db = local_client[MONGO_DB]


dm = DataManager()

# Storing futures
mongo_collection = remote_db['option_input_data']

quotes_collection = local_db['quotes_riskfreerate']
quotes_collection.create_index([('market', pymongo.ASCENDING)], unique=True)

data = list(mongo_collection.find({'idoptioninputsymbol': 15}).sort([('optioninputdatetime', 1)]))
idx = []
rfr = []
for row in data:
    idx.append(row['optioninputdatetime'])
    rfr.append(row['optioninputclose'])

rfr_series = pd.Series(rfr, index=idx).shift().dropna() / 100.0


rec = {
    'market': 'US',
    'rfr_series': lz4.block.compress(pickle.dumps(rfr_series))
}
quotes_collection.replace_one({'market': 'US'}, rec, upsert=True)


if len(rfr_series.ix[:datetime(2001, 4, 29, 12, 3).date()].tail(1)) > 0:
    print('ok')