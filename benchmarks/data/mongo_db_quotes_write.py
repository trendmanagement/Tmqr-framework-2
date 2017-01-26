from pymongo import MongoClient
from tmqr.settings import *
import numpy as np
from datetime import datetime, timedelta
import time
import pickle
import pandas as pd
import sys

TICKER = "RANDOM"

client = MongoClient(MONGO_CONNSTR)
db = client[MONGO_DB]

current_date = datetime(2010, 1, 10)


def write_pickled(dt, random_values):

    array = []
    for i, r in enumerate(random_values):
        record = {
            'dt': dt.replace(hour=0, minute=0, second=0) + timedelta(minutes=i),
            'o': r[0],
            'h': r[1],
            'l': r[2],
            'c': r[3],
            'v': r[4],
        }
        array.append(record)

    df = pd.DataFrame(array).set_index('dt')

    record = {
        'ticker': TICKER,
        'dt': dt.replace(hour=0, minute=0, second=0),
        'ohlc': pickle.dumps(df)
    }
    db['pickled_quotes'].insert(record)


def write_minute_by_minute(dt, random_values):

    for i, r in enumerate(random_values):
        record = {
            'ticker': TICKER,
            'dt': dt.replace(hour=0, minute=0, second=0) + timedelta(minutes=i),
            'o': r[0],
            'h': r[1],
            'l': r[2],
            'c': r[3],
            'v': r[4],
        }
        db['splitted_quotes'].insert(record)

def write_bundled_record(dt, random_values):
    record = {
        'ticker': TICKER,
        'dt': dt.replace(hour=0, minute=0, second=0),
    }
    ohlcs = {}
    for i, r in enumerate(random_values):
        d = dt.replace(hour=0, minute=0, second=0) + timedelta(minutes=i)

        minutes = ohlcs.setdefault(str(d.hour), {})

        minutes[str(d.minute)] = {
            'o': r[0],
            'h': r[1],
            'l': r[2],
            'c': r[3],
            'v': r[4],
        }
    record['ohlc'] = ohlcs
    db['bundled_quotes'].insert(record)


# Preventing MongoDB quote overwriting


rand_data = np.random.uniform(size=(60*24, 5))

time_pickle = time.time()
df = pd.DataFrame(rand_data)
n = 2560
for i in range(n):
    pcl_data = pickle.dumps(df)
    pickle.loads(pcl_data)
print("Pickle/Unpickle roundtrip {1} days {0}s".format((time.time() - time_pickle)/n, n))

print("Pickled object size: {0}".format(len(pcl_data)))

sys.exit(-2)
db['bundled_quotes'].drop()
db['splitted_quotes'].drop()
db['pickled_quotes'].drop()

while current_date < datetime.now():

    rand_data = np.random.uniform(size=(60*24, 5))

    time_splitted_begin = time.time()
    write_minute_by_minute(current_date, rand_data)
    time_splitted_end = time.time()

    time_bundled_begin = time.time()
    write_bundled_record(current_date, rand_data)
    time_bundled_end = time.time()

    time_pickled_begin = time.time()
    write_pickled(current_date, rand_data)
    time_pickled_end = time.time()

    print("{0} Splitted write: {1}s Bundled: {2}s Pickled: {3}s".format(current_date,
                                                          time_splitted_end-time_splitted_begin,
                                                          time_bundled_end-time_bundled_begin,
                                                          time_pickled_end-time_pickled_begin))
    current_date += timedelta(days=1)
print('Done')
