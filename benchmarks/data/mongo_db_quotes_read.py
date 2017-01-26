import time
from datetime import datetime

import pymongo
from pymongo import MongoClient

from tmqr.settings import *


class Timer(object):
    def __init__(self, action_txt):
        self.action_txt = action_txt

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.secs = self.end - self.start
        self.msecs = self.secs * 1000  # millisecs
        print('{0}: elapsed time: {1} ms'.format(self.action_txt, self.msecs))


TICKER = "RANDOM"

client = MongoClient(MONGO_CONNSTR)
db = client[MONGO_DB]

start_date = datetime(2011, 1, 10)
end_date = datetime(2016, 11, 10)


def read_pickled():
    db['pickled_quotes'].create_index([('ticker', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)])

    with Timer("Pickled Mongo query") as t:
        for rec in db['pickled_quotes'].find({'ticker': 'RANDOM', 'dt': {'$gte': start_date, '$lte': end_date}}):
            continue


def read_single():
    db['splitted_quotes'].create_index([('ticker', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)])

    with Timer("Splitted quotes Mongo query") as t:
        for rec in db['splitted_quotes'].find({'ticker': 'RANDOM', 'dt': {'$gte': start_date, '$lte': end_date}}):
            continue

def read_bundled():
    db['bundled_quotes'].create_index([('ticker', pymongo.ASCENDING), ('dt', pymongo.ASCENDING)])

    with Timer("Bundled quotes Mongo query") as t:
        for rec in db['bundled_quotes'].find({'ticker': 'RANDOM', 'dt': {'$gte': start_date, '$lte': end_date}}):
            continue

read_pickled()

read_single()

read_bundled()

print('Done')
