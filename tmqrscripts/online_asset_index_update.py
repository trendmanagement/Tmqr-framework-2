'''
Online asset index updates
First of all we need to maintain the new framework database in actual state, the asset index is a core of the system and should be updated on weekly basis (scheduled on the server by CRON).
I have implemented several notebooks to update new framework database so this code need to be bundled in standalone script.
Here is a full functional notebook for asset index updates: https://10.0.1.2:8889/notebooks/data/Import%20asset%20index.ipynb
'''

import sys, argparse, logging
import datetime
from decimal import Decimal
import pymongo
from pymongo import MongoClient


from tmqr.settings import *

try:
    from tmqr.settings_local import *
except:
    pass

# set up database connection
local_client = MongoClient(MONGO_CONNSTR)
local_db = local_client[MONGO_DB]

RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
RMT_MONGO_DB = 'tmldb_v2'

remomote_client = MongoClient(RMT_MONGO_CONNSTR)
remote_db = remomote_client[RMT_MONGO_DB]

# fill instruments dict from mongodb
instruments = {}
for row in remote_db['instruments'].find({}):
    instruments[row['idinstrument']] = row

# fill contracts dict from mongodb
contracts = {}

for data in remote_db['contracts'].find({}):
    tokens = data['contractname'].replace(',', '.').split('.')
    if '.' not in data['contractname'] or len(tokens) != 3:

        if 'F.' in data['contractname']:
            ctype = 'F'
            cmkt = 'US'
            cname = tokens[1]
            # print(cname)
        else:
            print('Wrong contract name: ' + data['contractname'])
            continue
    else:
        ctype, cmkt, cname = tokens

    idinstrument = data['idinstrument']

    if idinstrument not in instruments:
        print("idinstrument = {0} is not found for {1}".format(idinstrument, data['contractname']))
        continue

    underlying = instruments[idinstrument]['exchangesymbol']
    expiration = data['expirationdate']
    contract = '{0}.{1}{2}'.format(underlying,
                                   data['month'],
                                   str(int(data['year']))[2:])
    ticker = '{0}.{1}.{2}.{3}'.format(cmkt,
                                      ctype,
                                      contract,
                                      expiration.strftime('%y%m%d')
                                      )
    contracts[data['idcontract']] = {'tckr': ticker,
                                     'contr': contract,
                                     'type': ctype,
                                     'underlying': '{0}.{1}'.format(cmkt, underlying),
                                     'instr': '{0}.{1}'.format(cmkt, underlying),
                                     'exp': expiration,
                                     'mkt': cmkt,
                                     'extra_data': {
                                         'month': data['month'],
                                         'monthint': data['monthint'],
                                         'year': data['year'],
                                         'name': data['contractname'],
                                         'sqlid': data['idcontract'],
                                     }
                                     }
    # print(ticker)
    # break

# Init mongo asset index
mongo_db = local_db


mongo_collection = mongo_db['asset_index']

mongo_collection.create_index([('tckr', pymongo.ASCENDING)], unique=True)

mongo_collection.create_index([('contr', pymongo.ASCENDING),
                               ('mkt', pymongo.ASCENDING),
                               ('type', pymongo.ASCENDING)])

# Clean DB bad rounded strikes

from decimal import *

if False:

    for i in instruments.values():
        print(f"Cleaning: {i['exchangesymbol']}")
        strike_inc = i['optionstrikeincrement']

        if strike_inc - int(strike_inc) > 0:
            dec_points = 0
            strike = round(i['optionstrikeincrement'], 7)

            mongo_collection.delete_one({'instr': f"US.{i['exchangesymbol']}"})
            # print(f"{i['exchangesymbol']} {strike} {dec_points}")


# Storing futures

cnt = 0
dup_cnt = 0
for c in contracts.values():
    try:
        mongo_collection.replace_one({'tckr': c['tckr']}, c, upsert=True)
        cnt += 1
    except pymongo.errors.DuplicateKeyError:
        # print("Duplicated record: " + c['tckr'])
        dup_cnt += 1

print("Records added: {0} Duplicated: {1}".format(cnt, dup_cnt))


missed_cnt = 0
missed_contracts = []
cnt = 0
dup_cnt = 0
for data in remote_db['options'].find({}):
    # data = dict(map(convert_dates, row.items()))
    # print(data)
    ctype, cmkt, cname = data['optionname'].split('.')

    if data['idcontract'] not in contracts:
        missed_cnt += 1
        missed_contracts.append(data)
        continue

    underlying_dict = contracts[data['idcontract']]
    underlying = underlying_dict['tckr'].replace('US.', '').replace('.',
                                                                    '-')  # "{0}-{1}".format(underlying_dict['type'], underlying_dict['contr'])
    expiration = data['expirationdate']

    if 'optioncode' in data and data['optioncode'].strip() != '':
        ticker = '{0}.{1}.{2}.{5}.{7}@{6}'.format(cmkt,
                                                  ctype,
                                                  underlying,
                                                  data['optionmonth'],
                                                  str(int(data['optionyear']))[2:],
                                                  expiration.strftime('%y%m%d'),
                                                  round(data['strikeprice'], 7),
                                                  data['optioncode'].strip()
                                                  )
    else:
        ticker = '{0}.{1}.{2}.{5}@{6}'.format(cmkt,
                                              ctype,
                                              underlying,
                                              data['optionmonth'],
                                              str(int(data['optionyear']))[2:],
                                              expiration.strftime('%y%m%d'),
                                              round(data['strikeprice'], 7)
                                              )
    opt_record = {'tckr': ticker,
                  'type': ctype,
                  'underlying': underlying_dict['tckr'],
                  'exp': expiration,
                  'instr': underlying_dict['instr'],
                  'mkt': cmkt,
                  'opttype': data['callorput'],
                  'strike': data['strikeprice'],
                  'optcode': data.get('optioncode', ''),
                  'extra_data': {
                      'month': data['optionmonth'],
                      'monthint': data['optionmonthint'],
                      'year': data['optionyear'],
                      'name': data['optionname'],
                      'sqlid': data['idoption'],
                  }
                  }

    try:
        mongo_collection.replace_one({'tckr': opt_record['tckr']}, opt_record, upsert=True)
        cnt += 1
    except pymongo.errors.DuplicateKeyError:
        dup_cnt += 1

print("Records added: {0} Duplicated: {1}".format(cnt, dup_cnt))


print(f"Records with missed contract ID: {missed_cnt}")


for mc in missed_contracts:
    print(f"{mc['cqgsymbol']} IdContract: {mc['idcontract']}")


exchanges = {}
#colname = 'exchange'
#qry = 'SELECT * FROM cqgdb.tbl{0}'.format(colname)

#logging.debug(qry)
#c2 = sql_conn.cursor(as_dict=True)
#c2.execute(qry)

for row in remote_db['exchange'].find({}):
    exchanges[row['idexchange']] = row

EXCHANGE_NAMESPACE = 'US'

for iid, instr in instruments.items():
    # print(instr)
    res = {
        'tckr': "{0}.{1}".format(EXCHANGE_NAMESPACE, instr['exchangesymbol']),
        'ticksize': instr['ticksize'],
        'tickvalue': instr['tickvalue'],
        'mkt': EXCHANGE_NAMESPACE,
        'exchange': exchanges[instr['idexchange']]['exchange'],
        'description': instr['description'],
        'exchangesymbol': instr['exchangesymbol'],
        'extra_data': {
        }

    }
    res['extra_data'].update(exchanges[instr['idexchange']])
    #print(res)
    # if res['exchangesymbol'] == 'ES':
    #    print(res)
    #    break
