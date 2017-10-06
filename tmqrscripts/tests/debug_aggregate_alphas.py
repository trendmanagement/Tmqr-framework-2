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
final_alpha_list = []
for campaign_list in list(remote_db['accounts'].aggregate(pipeline)):

    for alpha_list in list(campaign_list['alphas_list'][0][0]['alphas']):
        alpha_list_replace = alpha_list.replace('!NEW_',"")
        final_alpha_list.append(alpha_list_replace)
# w = list(x[0]['alphas_list'][0][0]['alphas'])
# t.append(w)

print('6J_CallSpread_Short_Strategy_DSP_LPBP_Combination__Bearish_May_12_custom' in final_alpha_list)



