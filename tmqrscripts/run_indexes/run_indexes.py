

'''V1 package calls'''
from exobuilder.data.datasource_mongo import DataSourceMongo
from tradingcore.execution_manager import ExecutionManager
from exobuilder.data.assetindex_mongo import AssetIndexMongo
from exobuilder.data.exostorage import EXOStorage

from tradingcore.signalapp import SignalApp, APPCLASS_EXO, APPCLASS_ALPHA
from tradingcore.messages import *

try:
    '''C - compiled code, will not run on local machine'''
    from tmqrstrategy.strategy_base import StrategyBase
except:
    pass

from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase



from tmqr.logs import log
from datetime import datetime, time
import pytz
from tmqr.errors import DataEngineNotFoundError
import threading

import pymongo
from pymongo import MongoClient

'''
https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%201%20-%20Index%20EXO%20Long%20Call%20Rund%20%2B%20Deployment.ipynb

https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%202%20-%20Load%20deployed%20index%20from%20the%20DB.ipynb

https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%203%20-%20Getting%20indexes%20trading%20session%20params.ipynb
'''

class IndexGenerationScript:
    def __init__(self, override_run_exo=False, reset_exo_from_beginning = False, date_end = None, override_run_alpha=False):

        self.override_run_exo = override_run_exo
        self.reset_exo_from_beginning = reset_exo_from_beginning

        if override_run_alpha == None:
            self.override_run_alpha = False
        else:
            self.override_run_alpha = override_run_alpha

        self.client = MongoClient(MONGO_CONNSTR)
        self.db = self.client[MONGO_DB]
        self.date_start = datetime(2011,1,1)
        self.date_end = date_end

        self.db['alpha_data'].create_index(
            [('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
            unique=False)

        self.db['alpha_data'].create_index([('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
                                               unique=False)



        # RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
        # RMT_MONGO_DB = 'tmldb_v2'

        self.remote_client = MongoClient(MONGO_CONNSTR_V1)
        self.remote_db = self.remote_client[MONGO_EXO_DB_V1]

        self.campaign_alpha_list = self.get_campaign_alpha_list()

        self.signalapp_exo = SignalApp('V2 calcs', APPCLASS_EXO, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)
        self.signalapp_alpha = SignalApp('V2 calcs', APPCLASS_ALPHA, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)

    def run_all_instruments(self):
        self.run_main_index_alpha_script(INSTRUMENT_LIST_TO_RUN_INDEXES)

    def run_selected_intruments(self, instrument):
        instrument_list = []
        instrument_list.append(instrument)
        self.run_main_index_alpha_script(instrument_list)

    def run_main_index_alpha_script(self, instrument_list):
        '''
        runs the script for all instruments and indexes in settings_index and associated alphas
        :param override_run: runs regardless of time
        :return: 
        '''

        self.asset_info_collection = self.db['asset_info']

        #instrument_list = ['US.ES', 'US.CL', 'US.ZN', 'US.6C', 'US.6J', 'US.6E', 'US.6B']
        # instrument_list = ['US.ES', 'US.CL', 'US.ZN']
        # instrument_list = ['US.ES']

        for instrument in self.asset_info_collection.find({}):
        # instrument = {'instrument':'US.ES'}
        # instrument = {'instrument':'US.6J'}
            if not 'DEFAULT' in instrument['instrument'] and instrument['instrument'] in instrument_list:
                print(instrument['instrument'])
                for exo in INDEX_LIST:
                    if 'instrument' in exo:
                        # print(exo['instrument'])
                        if instrument['instrument'] == exo['instrument']:
                            t = threading.Thread(target=self.run_through_each_index_threads, args=(instrument['instrument'], exo, True))
                            t.start()
                            # self.run_through_each_index_threads(instrument['instrument'], exo, True)
                            # pass
                    else:
                        t = threading.Thread(target=self.run_through_each_index_threads, args=(instrument['instrument'], exo))
                        t.start()
                        # self.run_through_each_index_threads(instrument['instrument'], exo)
                        # pass



    def run_through_each_index_threads(self,instrument, exo_index, instrument_specific = False):
        '''
        runs through the creation and saving logic for each index and alpha
        only runs indexes on Mon-Fri
        runs alphas Mon-Sun
        :param instrument: 
        :param exo_index: 
        :return: 
        '''
        ExoClass = exo_index['class']
        try:

            index_hedge_name = '{0}_{1}'.format(instrument,ExoClass._index_name)

            if self.date_end is None:
                dm = DataManager(date_start=self.date_start)
            else:
                dm = DataManager(date_start=self.date_start, date_end=self.date_end)


            if self.reset_exo_from_beginning:
                index = self.create_index_class(instrument, ExoClass, dm, instrument_specific)

                #current_time = datetime.utcnow()

                #current_time_utc = datetime.utcnow()

                ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE))

                self.run_index(index, ct['current_time_utc'], index_hedge_name, creating_index=True)

                self.checking_alpha_then_run(index, ct['current_time'], ct['current_time_utc'], index_hedge_name)
            else:

                index = IndexBase.load(dm, index_hedge_name)

                # current_time = datetime.now(index.session.tz)

                # current_time_utc = self.time_to_utc_from_local_tz(current_time, index.session.tz.zone)

                ct = self.current_time_generate(index.session.tz)

                sess_start, sess_decision, sess_exec, next_sess_date = index.session.get(ct['current_time'],
                                                                    decision_time_shift=index.decision_time_shift - 1)


                index_from_db = self.db['index_data'].find_one({'name': index_hedge_name})

                if index_from_db == None or not 'index_update_time' in index_from_db['context']:
                    self.run_index(index, ct['current_time_utc'], index_hedge_name)
                else:
                    #last_index_update_time = pytz.timezone(index.session.tz.zone).localize(index_from_db['context']['index_update_time'])
                    last_index_update_time = self.time_to_utc_from_none(index_from_db['context']['index_update_time'])
                    last_index_update_time = self.utc_to_time(last_index_update_time,index.session.tz.zone)

                    if self.override_run_exo or (ct['current_time'].weekday() < 5 and\
                            ((ct['current_time'] >= sess_decision and last_index_update_time < sess_decision)
                             or (ct['current_time'] >= sess_exec and last_index_update_time < sess_exec))):

                        self.run_index(index, ct['current_time_utc'], index_hedge_name)

                self.checking_alpha_then_run(index, ct['current_time'], ct['current_time_utc'], index_hedge_name)


        except (DataEngineNotFoundError, NotImplementedError) as e:
            log.warn(f"ExoIndexError: '{e}'")

            try:

                index = self.create_index_class(instrument, ExoClass, dm, instrument_specific)

                ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE))

                self.run_index(index, ct['current_time_utc'], index_hedge_name, creating_index=True)

                self.checking_alpha_then_run(index, ct['current_time'], ct['current_time_utc'], index_hedge_name)

            except Exception as e1:
                log.warn(f"ExoIndexError: '{e1}'")

    def current_time_generate(self, tz):
        assert tz != None, 'no timezone passed to current_time_generate'

        ct = {}

        ct['current_time'] = datetime.now(tz)

        ct['current_time_utc'] = self.time_to_utc_from_local_tz(ct['current_time'], tz.zone)

        return ct



    def create_index_class(self, instrument, ExoClass, dm, instrument_specific):
        '''
        creates the index class taking into account instrument specific (a class specific to instrument) and option codes
        :param instrument: 
        :param ExoClass: 
        :param dm: 
        :param instrument_specific: 
        :return: 
        '''

        INDEX_CONTEXT = {
            'instrument': instrument,
            'context': {'costs_futures': 3.0,
                        'costs_options': 3.0}
        }

        if not instrument_specific:
            opt_codes_to_pass = []

            for inst_opt_code in INSTRUMENT_OPT_CODE_LIST:
                if instrument == inst_opt_code['instrument']:
                    opt_codes_to_pass = inst_opt_code['opt_codes']
                    break

            INDEX_CONTEXT['context']['opt_codes'] = opt_codes_to_pass

        index = ExoClass(dm, **INDEX_CONTEXT)
        return index
        #pass

    def run_index(self, index, update_time, index_hedge_name, creating_index = False):
        '''
        runs and saves the index
        :param index: 
        :param update_time: 
        :param index_hedge_name: 
        :return: 
        '''

        # if not creating_index:
        try:
            self.db['index_data'].update_one({'name': index_hedge_name},
                                     {'$set': {'context.index_update_time': update_time}})
        except:
            pass

        index.run()
        index.save()

        # if creating_index:
        self.db['index_data'].update_one({'name': index_hedge_name},
                                     {'$set': {'context.index_update_time': update_time}})

        self.signalapp_exo.send(MsgStatus('V2_Index', 'V2 Index finished {0}'.format(index_hedge_name), notify=True))
        #pass



    def checking_alpha_then_run(self,index,current_time, current_time_utc, index_hedge_name):
        '''
        This runs the alphas based on time and if the V1 alphas have run
        :param index: 
        :param current_time: 
        :param current_time_utc: 
        :param index_hedge_name: 
        :return: 
        '''
        alpha_sess_start, alpha_sess_decision, alpha_sess_exec, alpha_next_sess_date = index.session.get(
            current_time, 0)



        if self.reset_exo_from_beginning or self.override_run_exo or current_time >= alpha_sess_decision:
            alphas_list = list(self.db['alpha_data'].find({'context.index_hedge_name': index_hedge_name}))

            v1_alpha_ok = True

            for alpha in alphas_list:
                # print('running 1 ' + alpha['name'])

                if alpha['name'] in self.campaign_alpha_list or self.override_run_alpha :

                    '''
                    below checks if v1 alpha has been calculated                    
                    '''
                    if 'v1_alphas' in alpha['context']:
                        swarm_list = alpha['context']['v1_alphas']

                        if swarm_list:
                            earliest_date = current_time.date()
                            for swarm in swarm_list:

                                v1_alpha = self.remote_db['swarms'].find_one({'swarm_name': swarm})

                                if v1_alpha['last_date'].date() < earliest_date:
                                    earliest_date = v1_alpha['last_date'].date()
                                    v1_alpha_ok = False

                                if not v1_alpha_ok:
                                    current_time_utc = self.time_to_utc_from_local_tz(datetime.combine(earliest_date, time(0, 0, 0)), index.session.tz.zone)


                    if not 'alpha_update_time' in alpha['context']:
                        # t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                        # t.start()
                        self.run_alpha(alpha['name'], current_time_utc)
                        # print('running 2 ' + alpha['name'])

                    else:
                        last_alpha_update_time = self.time_to_utc_from_none(alpha['context']['alpha_update_time'])
                        last_alpha_update_time = self.utc_to_time(last_alpha_update_time, index.session.tz.zone)


                        if self.reset_exo_from_beginning or self.override_run_exo:
                            # t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                            # t.start()
                            self.run_alpha(alpha['name'], current_time_utc)
                        elif last_alpha_update_time < alpha_sess_decision and v1_alpha_ok:
                            #check V1 alpha update
                            # t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                            # t.start()
                            self.run_alpha(alpha['name'], current_time_utc)
                            # print('running 3 ' + alpha['name'])


    def run_alpha(self, alpha_name, update_time):
        '''
        alpha run and save
        :param alpha_name: 
        :param update_time: 
        :return: 
        '''
        # try:

        self.db['alpha_data'].update_one({'name': alpha_name},
                                         {'$set': {'context.alpha_update_time': update_time}})

        if self.date_end is None:
            dm2 = DataManager()
        else:
            dm2 = DataManager(date_start=self.date_start, date_end=self.date_end)
        #print(alpha_name)
        saved_alpha = StrategyBase.load(dm2, alpha_name)
        saved_alpha.run()
        saved_alpha.save()

        #print('running finished ' + alpha_name)

        self.db['alpha_data'].update_one({'name': alpha_name},
                                         {'$set': {'context.alpha_end_update_time': update_time}})

        self.signalapp_alpha.send(MsgStatus('V2_Alpha', 'V2 Alpha finished {0}'.format(alpha_name), notify=True))

        # self.run_account_positions_process()



        #log.warn('running finished ' + alpha_name)

        # except:

    def get_campaign_alpha_list(self):
        '''
        this gets the full list of alphas that the current active campaigns use
        :return: the list of alphas that the campaigns use
        '''
        pipeline = [
            {
                '$lookup':
                    {
                        'from': 'campaigns',
                        'localField': 'campaign_name',
                        'foreignField': 'name',
                        'as': 'alphas'
                    }
            },
            {'$group': {'_id': '$campaign_name', 'alphas_list': {'$push': '$alphas'}}}

        ]
        final_alpha_list = []
        for campaign_list in list(self.remote_db['accounts'].aggregate(pipeline)):

            for alpha_list in list(campaign_list['alphas_list'][0][0]['alphas']):
                alpha_list_replace = alpha_list.replace('!NEW_', "")
                final_alpha_list.append(alpha_list_replace)

        return final_alpha_list

    def run_account_positions_process(self):
        '''
        this updates the account position to the db for realtime
        :return: 
        '''

        try:
            assetindex = AssetIndexMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
            storage = EXOStorage(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1)
            datasource = DataSourceMongo(MONGO_CONNSTR_V1, MONGO_EXO_DB_V1, assetindex, futures_limit=10, options_limit=10,
                                         exostorage=storage)

            exmgr = ExecutionManager(MONGO_CONNSTR_V1, datasource, MONGO_EXO_DB_V1)
            exmgr.account_positions_process(write_to_db=True)
        except Exception as e:
            print(e)
            #pass

    def time_to_utc_from_none(self, naive):
        return naive.replace(tzinfo=pytz.utc)


    def time_to_utc_from_local_tz(self, local_dt, timezone):
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt

    def time_to_utc(self, naive, timezone):
        local = pytz.timezone(timezone)
        local_dt = local.localize(naive)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt

    def utc_to_time(self, naive, timezone):
        return naive.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone))


if __name__ == "__main__":
    igs = IndexGenerationScript()
    igs.run_all_instruments()








