
from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase

from tmqrstrategy.strategy_base import StrategyBase

from tmqr.logs import log
from datetime import datetime
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
    def __init__(self):
        self.client = MongoClient(MONGO_CONNSTR)
        self.db = self.client[MONGO_DB]
        self.date_start = datetime(2011,1,1)

        self.db['alpha_data'].create_index(
            [('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
            unique=False)

        self.db['alpha_data'].create_index([('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
                                               unique=False)

    def run_main_index_alpha_script(self):
        '''
        runs the script for all instruments and indexes in settings_index and associated alphas
        :return: 
        '''
        self.asset_info_collection = self.db['asset_info']

        for instrument in self.asset_info_collection.find({}):
            if not 'DEFAULT' in instrument['instrument']:
                for exo in INDEX_LIST:
                    t = threading.Thread(target=self.run_through_each_index_threads, args=(instrument['instrument'], exo))
                    t.start()

        #for exo in INDEX_LIST:
        #    self.run_through_each_index_threads('US.ES', exo)

        # for instrument in self.asset_info_collection.find({}):
        #     if not 'DEFAULT' in instrument['instrument']:
        #         for exo in INDEX_LIST:
        #             self.run_through_each_index_threads(instrument['instrument'], exo)

    def run_through_each_index_threads(self,instrument, exo_index):
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

            dm = DataManager(date_start=self.date_start)
            index = IndexBase.load(dm, index_hedge_name)

            current_time = datetime.now(index.session.tz)

            sess_start, sess_decision, sess_exec, next_sess_date = index.session.get(current_time,
                                                                                     decision_time_shift=index.decision_time_shift - 1)


            index_from_db = self.db['index_data'].find_one({'name': index_hedge_name})

            if index_from_db == None or not 'index_update_time' in index_from_db['context']:
                self.run_index(index, current_time, index_hedge_name)
            else:
                last_index_update_time = index_from_db['context']['index_update_time']

                if current_time.weekday() < 5 and\
                        ((current_time >= sess_decision and last_index_update_time < sess_decision)
                         or (current_time >= sess_exec and last_index_update_time < sess_exec)):

                    self.run_index(index, current_time, index_hedge_name)

            self.checking_alpha_then_run(index, current_time, index_hedge_name)


        except (DataEngineNotFoundError, NotImplementedError) as e:
            log.warn(f"ExoIndexError: '{e}'")

            try:

                opt_codes_to_pass = []

                for inst_opt_code in INSTRUMENT_OPT_CODE_LIST:
                    if instrument == inst_opt_code['instrument']:
                        opt_codes_to_pass = inst_opt_code['opt_codes']
                        break

                index = ExoClass(dm, instrument=instrument, opt_codes=opt_codes_to_pass)

                self.run_index(index, current_time, index_hedge_name)

                self.checking_alpha_then_run(index, current_time, index_hedge_name)

            except:
                pass

    def run_index(self, index, update_time, index_hedge_name):
        index.run()
        index.save()
        self.db['index_data'].update_one({'name': index_hedge_name},
                                            {'$set': {'context.index_update_time': update_time}})



    def checking_alpha_then_run(self,index,current_time,index_hedge_name):
        alpha_sess_start, alpha_sess_decision, alpha_sess_exec, alpha_next_sess_date = index.session.get(
            current_time, 0)

        if current_time >= alpha_sess_start:
            alphas_list = list(self.db['alpha_data'].find({'context.index_hedge_name': index_hedge_name}))

            for alpha in alphas_list:
                if not 'alpha_update_time' in alpha['context']:
                    t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time))
                    t.start()

                elif alpha['context']['alpha_update_time'] < alpha_sess_start:
                    t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time))
                    t.start()


    def run_alpha(self, alpha_name, update_time):
        '''
        alpha run and save
        :param alpha_name: 
        :param update_time: 
        :return: 
        '''
        try:
            dm2 = DataManager()
            #print(alpha_name)
            saved_alpha = StrategyBase.load(dm2, alpha_name)
            saved_alpha.run()
            saved_alpha.save()

            print(alpha_name)

            self.db['alpha_data'].update_one({'name': alpha_name},
                                                {'$set': {'context.alpha_update_time': update_time}})

        except:
            pass



x = IndexGenerationScript()
x.run_main_index_alpha_script()





