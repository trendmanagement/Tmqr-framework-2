
from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase

from tmqrstrategy.strategy_base import StrategyBase

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
    def __init__(self, override_run=False, reset_from_beginning = False):

        self.override_run = override_run
        self.reset_from_beginning = reset_from_beginning

        self.client = MongoClient(MONGO_CONNSTR)
        self.db = self.client[MONGO_DB]
        self.date_start = datetime(2011,1,1)

        self.db['alpha_data'].create_index(
            [('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
            unique=False)

        self.db['alpha_data'].create_index([('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
                                               unique=False)

        RMT_MONGO_CONNSTR = 'mongodb://tmqr:tmqr@10.0.1.2/tmldb_v2?authMechanism=SCRAM-SHA-1'
        RMT_MONGO_DB = 'tmldb_v2'
        self.remote_client = MongoClient(RMT_MONGO_CONNSTR)
        self.remote_db = self.remote_client[RMT_MONGO_DB]

    def run_main_index_alpha_script(self):
        '''
        runs the script for all instruments and indexes in settings_index and associated alphas
        :param override_run: runs regardless of time
        :return: 
        '''

        self.asset_info_collection = self.db['asset_info']

        #instrument_list = ['US.ES', 'US.CL', 'US.ZN', 'US.6C', 'US.6J', 'US.6E', 'US.6B']
        instrument_list = ['US.ES', 'US.CL', 'US.ZN']

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
                    else:
                        t = threading.Thread(target=self.run_through_each_index_threads,
                                             args=(instrument['instrument'], exo))
                        t.start()
                        # self.run_through_each_index_threads(instrument['instrument'], exo)



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

            dm = DataManager(date_start=self.date_start)


            if self.reset_from_beginning:
                index = self.create_index_class(instrument, ExoClass, dm, instrument_specific)

                #current_time = datetime.utcnow()

                #current_time_utc = datetime.utcnow()

                ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE))

                self.run_index(index, ct['current_time_utc'], index_hedge_name)

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

                    if self.override_run or (ct['current_time'].weekday() < 5 and\
                            ((ct['current_time'] >= sess_decision and last_index_update_time < sess_decision)
                             or (ct['current_time'] >= sess_exec and last_index_update_time < sess_exec))):

                        self.run_index(index, ct['current_time_utc'], index_hedge_name)

                self.checking_alpha_then_run(index, ct['current_time'], ct['current_time_utc'], index_hedge_name)


        except (DataEngineNotFoundError, NotImplementedError) as e:
            log.warn(f"ExoIndexError: '{e}'")

            try:

                index = self.create_index_class(instrument, ExoClass, dm, instrument_specific)

                ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE))

                self.run_index(index, ct['current_time_utc'], index_hedge_name)

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

            INDEX_CONTEXT['opt_codes'] = opt_codes_to_pass

        index = ExoClass(dm, **INDEX_CONTEXT)
        return index
        #pass

    def run_index(self, index, update_time, index_hedge_name):
        index.run()
        index.save()

        self.db['index_data'].update_one({'name': index_hedge_name},
                                            {'$set': {'context.index_update_time': update_time}})
        #pass



    def checking_alpha_then_run(self,index,current_time, current_time_utc, index_hedge_name):
        alpha_sess_start, alpha_sess_decision, alpha_sess_exec, alpha_next_sess_date = index.session.get(
            current_time, 0)



        if self.reset_from_beginning or self.override_run or current_time >= alpha_sess_decision:
            alphas_list = list(self.db['alpha_data'].find({'context.index_hedge_name': index_hedge_name}))

            v1_alpha_ok = True

            for alpha in alphas_list:
                # print('running 1 ' + alpha['name'])



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
                    t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                    t.start()
                    # self.run_alpha(alpha['name'], current_time_utc)
                    # print('running 2 ' + alpha['name'])

                else:
                    last_alpha_update_time = self.time_to_utc_from_none(alpha['context']['alpha_update_time'])
                    last_alpha_update_time = self.utc_to_time(last_alpha_update_time, index.session.tz.zone)


                    if self.reset_from_beginning or self.override_run:
                        t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                        t.start()
                    elif last_alpha_update_time < alpha_sess_decision and v1_alpha_ok:
                        #check V1 alpha update

                        t = threading.Thread(target=self.run_alpha, args=(alpha['name'], current_time_utc))
                        t.start()
                        # self.run_alpha(alpha['name'], current_time_utc)
                        # print('running 3 ' + alpha['name'])


    def run_alpha(self, alpha_name, update_time):
        '''
        alpha run and save
        :param alpha_name: 
        :param update_time: 
        :return: 
        '''
        # try:
        dm2 = DataManager()
        #print(alpha_name)
        saved_alpha = StrategyBase.load(dm2, alpha_name)
        saved_alpha.run()
        saved_alpha.save()

        print('running finished ' + alpha_name)

        self.db['alpha_data'].update_one({'name': alpha_name},
                                            {'$set': {'context.alpha_update_time': update_time}})

        #log.warn('running finished ' + alpha_name)

        # except:


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











