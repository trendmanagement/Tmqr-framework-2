from exobuilder.data.datasource_mongo import DataSourceMongo
from tradingcore.execution_manager import ExecutionManager
from exobuilder.data.assetindex_mongo import AssetIndexMongo
from exobuilder.data.exostorage import EXOStorage

import pymongo
from tmqr.settings import *
import pytz
from pymongo import MongoClient
from tradingcore.execution_manager import ExecutionManager
from tradingcore.messages import *
from tradingcore.signalapp import SignalApp, APPCLASS_SIGNALS

from tmqr.settings import *


class CampaignUpdateCheckPushToRealtime:
    def __init__(self):

        self.client_v2 = MongoClient(MONGO_CONNSTR)
        self.db_v2 = self.client_v2[MONGO_DB]

        self.client_v1 = MongoClient(MONGO_CONNSTR_V1)
        self.db_v1 = self.client_v1[MONGO_EXO_DB_V1]
        self.db_v1['campaigns'].create_index(
            [('name', pymongo.ASCENDING)],
            unique=False)
        self.db_v1['swarms'].create_index(
            [('swarm_name', pymongo.ASCENDING)],
            unique=False)

        self.signalapp_exo = SignalApp('Campaign Status', APPCLASS_SIGNALS, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)

    def run_query_to_test_campaign_components(self):


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

        #current_time_local = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))
        current_date_local = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).date()

        current_time_utc = datetime.utcnow()
        current_date_utc = current_time_utc.date()

        campaign_ready_to_push_to_realtime = False;

        for campaign_list in list(self.db_v1['accounts'].aggregate(pipeline)):

            if not ('context' in campaign_list['alphas_list'][0][0] \
                            and 'update_time' in campaign_list['alphas_list'][0][0]['context']) or \
                            current_date_utc != campaign_list['alphas_list'][0][0]['context']['update_time'].date():
                # pass
            # else:

                campaign_ready = True
                # print(campaign_list['alphas_list'][0][0]['name'])

                for alpha in list(campaign_list['alphas_list'][0][0]['alphas']):
                    if "!NEW_" in alpha:
                        alpha_v2 = alpha.replace('!NEW_',"")

                        alpha_v2_obj = self.db_v2['alpha_data'].find_one({'name':alpha_v2})

                        alpha_v2_datetime = alpha_v2_obj['context']['alpha_end_update_time']

                        if alpha_v2_datetime.date() != current_date_utc:
                            campaign_ready = False
                            break
                    else:
                        v1_alpha = self.db_v1['swarms'].find_one({'swarm_name': alpha})
                        if v1_alpha['last_date'].date() != current_date_local:
                            campaign_ready = False
                            break

                if campaign_ready:

                    self.signalapp_exo.send(
                        MsgStatus('Campaign Status', 'Ready {0}'.format(campaign_list['alphas_list'][0][0]['name']), notify=True))

                    self.db_v1['campaigns'].update_one({'name': campaign_list['alphas_list'][0][0]['name']},
                                                     {'$set': {'context.update_time': current_time_utc}})

                    campaign_ready_to_push_to_realtime = True

                    print('campaign ready', campaign_list['alphas_list'][0][0]['name'])

        if campaign_ready_to_push_to_realtime:
            assetindex = AssetIndexMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
            storage = EXOStorage(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
            datasource = DataSourceMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1, assetindex, futures_limit=10,
                                         options_limit=10,
                                         exostorage=storage)

            exmgr = ExecutionManager(MONGO_CONNSTR_V1, datasource, dbname=MONGO_EXO_DB_V1)
            exmgr.account_positions_process(write_to_db=True)
            # pass


if __name__ == "__main__":
    cuc = CampaignUpdateCheckPushToRealtime()
    cuc.run_query_to_test_campaign_components()


