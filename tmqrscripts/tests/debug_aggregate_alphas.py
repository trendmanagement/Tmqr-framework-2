from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase

import pymongo
from pymongo import MongoClient

RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
RMT_MONGO_DB = 'tmldb_v2'


remote_client = MongoClient(MONGO_CONNSTR_V1)
remote_db = remote_client[MONGO_EXO_DB_V1]

mongo_client_v2 = MongoClient(MONGO_CONNSTR)
mongo_db_v2 = mongo_client_v2[MONGO_DB]

from bson.son import SON

pipeline = [
{
    '$lookup':
    {
        'from':'campaigns',
        'localField':'campaign_name',
        'foreignField':'name',
        'as':'alphas'
        }
  },
  {'$group':{'_id':'$campaign_name','alphas_list':{'$push':'$alphas'}}}

]
# final_alpha_list = []
# for campaign_list in list(remote_db['accounts'].aggregate(pipeline)):
#
#     for alpha_list in list(campaign_list['alphas_list'][0][0]['alphas']):
#         alpha_list_replace = alpha_list.replace('!NEW_',"")
#         final_alpha_list.append(alpha_list_replace)
#
# print('6J_CallSpread_Short_Strategy_DSP_LPBP_Combination__Bearish_May_12_custom' in final_alpha_list)

final_alpha_list = []
for campaign_list in list(remote_db['accounts'].aggregate(pipeline)):

    for alpha_list in list(campaign_list['alphas_list'][0][0]['alphas']):
        for alpha in alpha_list:
            if "!NEW_" in alpha:
                alpha_v2 = alpha.replace('!NEW_',"")
                print(alpha_v2)
                final_alpha_list.append(alpha_v2)

print(final_alpha_list)

x = (mongo_db_v2['alpha_data'].find({'name': {'$in': final_alpha_list}}))
# print(list(x))
ww = []
for g in x:
    ww.append(g['context']['index_hedge_name'])
# print(g['context']['index_hedge_name'])

print(ww)


