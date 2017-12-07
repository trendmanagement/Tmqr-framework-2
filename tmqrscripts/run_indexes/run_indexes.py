

'''V1 package calls'''
from exobuilder.data.datasource_mongo import DataSourceMongo
from tradingcore.execution_manager import ExecutionManager
from exobuilder.data.assetindex_mongo import AssetIndexMongo
from exobuilder.data.exostorage import EXOStorage

from tradingcore.signalapp import SignalApp, APPCLASS_EXO, APPCLASS_ALPHA
from tradingcore.messages import *

'''smartcampaign import'''
from smartcampaign import SmartCampaignBase

try:
    '''C - compiled code, will not run on local machine'''
    from tmqrstrategy.strategy_base import StrategyBase
except:
    pass

from tmqrscripts.index_scripts.settings_index import *
from tmqr.settings import *
from tmqrfeed.manager import DataManager
from tmqrindex import IndexBase



# from tmqr.logs import log
import os
import logging as log
filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'exo_alpha.log')
log.basicConfig(filename=filename,level=log.DEBUG, format='%(asctime)s %(message)s')

from datetime import datetime, time
import pytz
from tmqr.errors import DataEngineNotFoundError
# import threading

# log.disabled = True

import pymongo
from pymongo import MongoClient

'''
https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%201%20-%20Index%20EXO%20Long%20Call%20Rund%20%2B%20Deployment.ipynb

https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%202%20-%20Load%20deployed%20index%20from%20the%20DB.ipynb

https://10.0.1.2:8889/notebooks/indexes/index_deployment_samples/Step%203%20-%20Getting%20indexes%20trading%20session%20params.ipynb
'''

class IndexGenerationScript:
    def __init__(self, override_time_check_run_exo=False, reset_exo_from_beginning = False, date_end = None, override_run_alpha=False, try_run_all_exos_live_and_test = False,
                 instrument=None, run_only_test_exos = False):

        log.debug('Running exo alpha update')

        if override_time_check_run_exo == None:
            self.override_time_check_run_exo = False
        else:
            self.override_time_check_run_exo = override_time_check_run_exo

        if reset_exo_from_beginning == None:
            self.reset_exo_from_beginning = False
        else:
            self.reset_exo_from_beginning = reset_exo_from_beginning

        if override_run_alpha == None:
            self.override_run_alpha = False
        else:
            self.override_run_alpha = override_run_alpha

        if try_run_all_exos_live_and_test == None:
            self.try_run_all_exos_live_and_test = False
        else:
            self.try_run_all_exos_live_and_test = try_run_all_exos_live_and_test

        if run_only_test_exos == None:
            self.run_only_test_exos = False
        else:
            self.run_only_test_exos = run_only_test_exos

        if instrument == None:
            self.instrument_list = INSTRUMENT_LIST_TO_RUN_INDEXES
        else:
            self.instrument_list = []
            self.instrument_list.append(instrument)



        mongo_client_v2 = MongoClient(MONGO_CONNSTR)
        self.mongo_db_v2 = mongo_client_v2[MONGO_DB]

        self.date_start = datetime(2011,1,1)
        self.date_end = date_end

        self.mongo_db_v2['alpha_data'].create_index(
            [('context.index_hedge_name', pymongo.ASCENDING), ('type', pymongo.ASCENDING)],
            unique=False)

        mongo_client_v1 = MongoClient(MONGO_CONNSTR_V1)
        self.mongo_db_v1 = mongo_client_v1[MONGO_EXO_DB_V1]
        # self.mongo_db_v1['alpha_data'].create_index(
        #     [('name', pymongo.ASCENDING)],
        #     unique=False)

        self.campaign_alpha_list = self.get_campaign_alpha_list()

        self.campaign_exo_list = self.get_campaign_exo_list(self.campaign_alpha_list)

        self.signalapp_exo = SignalApp('V2 calcs', APPCLASS_EXO, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)
        # self.signalapp_alpha = SignalApp('V2 calcs', APPCLASS_ALPHA, RABBIT_HOST, RABBIT_USER, RABBIT_PASSW)

    # def run(self):
    #     self.run_main_index_alpha_script(self.instrument_list)


    # def run_selected_intruments(self, instrument):
    #     instrument_list = []
    #     instrument_list.append(instrument)
    #     self.run_main_index_alpha_script(instrument_list)

    def run_main_index_alpha_script(self):
        '''
        runs the script for all instruments and indexes in settings_index and associated alphas
        :param override_run: runs regardless of time
        :return: 
        '''

        self.asset_info_collection = self.mongo_db_v2['asset_info']

        #instrument_list = ['US.ES', 'US.CL', 'US.ZN', 'US.6C', 'US.6J', 'US.6E', 'US.6B']

        for instrument in self.asset_info_collection.find({},{'instrument':1,'last_bar_update':1}):
        # instrument = {'instrument':'US.ES'}
        # instrument = {'instrument':'US.6J'}
            if not 'DEFAULT' in instrument['instrument'] and instrument['instrument'] in self.instrument_list:

                log.debug(instrument['instrument'])

                for exo in INDEX_LIST:

                    instrument_specific = 'instrument' in exo and instrument['instrument'] == exo['instrument']

                    if instrument_specific or not 'instrument' in exo:
                        # t = threading.Thread(target=self.run_through_each_index_threads, args=(instrument['instrument'], exo, instrument_specific))
                        # t.start()

                        last_bar_update = None
                        if 'last_bar_update' in instrument:
                            last_bar_update = instrument['last_bar_update']

                        self.run_through_each_index_threads(instrument['instrument'], last_bar_update, exo, instrument_specific)


    def run_through_each_index_threads(self, instrument_symbol, last_bar_update, exo_index, instrument_specific = False):
        '''
        runs through the creation and saving logic for each index and alpha
        only runs indexes on Mon-Fri
        runs alphas Mon-Sun
        :param instrument_symbol: 
        :param exo_index: 
        :return: 
        '''

        mongo_db_v1 = self.mongo_db_v1

        ExoClass = exo_index['class']

        index_hedge_name = '{0}_{1}'.format(instrument_symbol, ExoClass._index_name)

        if not self.run_only_test_exos and (self.try_run_all_exos_live_and_test or index_hedge_name in self.campaign_exo_list) \
                or (self.run_only_test_exos and index_hedge_name not in self.campaign_exo_list):

            try:

                if self.date_end is None:
                    dm = DataManager(date_start=self.date_start)
                else:
                    dm = DataManager(date_start=self.date_start, date_end=self.date_end)


                if self.reset_exo_from_beginning:
                    index = self.create_index_class(instrument_symbol, ExoClass, dm, instrument_specific)

                    ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE), last_bar_update)

                    self.run_index(index, ct['last_bar_time_utc'], index_hedge_name, creating_index=True)

                    self.checking_alpha_then_run(index, ct['current_time'], ct['last_bar_time'], ct['last_bar_time_utc'], index_hedge_name, mongo_db_v1)
                else:

                    index = IndexBase.load(dm, index_hedge_name)

                    ct = self.current_time_generate(index.session.tz, last_bar_update)

                    sess_start, sess_decision, sess_exec, next_sess_date = index.session.get(ct['current_time'],
                                                                        decision_time_shift=index.decision_time_shift - 1)

                    index_from_db = self.mongo_db_v2['index_data'].find_one({'name': index_hedge_name},{'context':1})

                    if index_from_db == None or not 'index_update_time' in index_from_db['context']:
                        self.run_index(index, ct['last_bar_time_utc'], index_hedge_name)
                    else:
                        last_index_update_time = self.time_to_utc_from_none(index_from_db['context']['index_update_time'])
                        last_index_update_time = self.utc_to_time(last_index_update_time,index.session.tz.zone)




                        if self.override_time_check_run_exo or (ct['last_bar_time'].weekday() < 5 and\
                                ((ct['last_bar_time'] >= sess_decision and last_index_update_time < sess_decision)
                                 or (ct['last_bar_time'] >= sess_exec and last_index_update_time < sess_exec))):

                            self.run_index(index, ct['last_bar_time_utc'], index_hedge_name)

                    self.checking_alpha_then_run(index, ct['current_time'], ct['last_bar_time'], ct['last_bar_time_utc'], index_hedge_name, mongo_db_v1)


            except (DataEngineNotFoundError, NotImplementedError) as e:
                log.warning(f"ExoIndexError: '{e}'")

                try:

                    index = self.create_index_class(instrument_symbol, ExoClass, dm, instrument_specific)

                    ct = self.current_time_generate(pytz.timezone(DEFAULT_TIMEZONE), last_bar_update)

                    self.run_index(index, ct['last_bar_time_utc'], index_hedge_name, creating_index=True)

                    self.checking_alpha_then_run(index, ct['current_time'], ct['last_bar_time'], ct['last_bar_time_utc'], index_hedge_name, mongo_db_v1)

                except Exception as e1:
                    log.warning(f"ExoIndexError: '{e1}'")

    def current_time_generate(self, tz, last_bar_update=None):

        assert tz != None, 'no timezone passed to current_time_generate'

        ct = {}

        ct['current_time'] = datetime.now(tz)

        ct['current_time_utc'] = self.time_to_utc_from_local_tz(ct['current_time'], tz.zone)

        if last_bar_update is None:

            ct['last_bar_time'] = ct['current_time']

            ct['last_bar_time_utc'] = ct['current_time_utc']

        else:
            ct['last_bar_time'] = self.time_to_utc_from_none(last_bar_update)

            ct['last_bar_time_utc'] = self.utc_to_time(last_bar_update,tz.zone)



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
            # self.mongo_db_v2['index_data'].update_one({'name': index_hedge_name},
            #                                           {'$set': {'context.index_update_time': update_time}})

            index.run()
            index.save()

            # if creating_index:
            self.mongo_db_v2['index_data'].update_one({'name': index_hedge_name},
                                                      {'$set': {'context.index_update_time': update_time}})

        except Exception as e:
            log.warning("Failed Index {0}".format(index_hedge_name) )
            log.exception(e)
            self.signalapp_exo.send(
                MsgStatus('V2_Index', 'V2 Index Error {0}'.format(index_hedge_name), notify=True))

        # self.signalapp_exo.send(MsgStatus('V2_Index', 'V2 Index finished {0}'.format(index_hedge_name), notify=True))
        #pass



    def checking_alpha_then_run(self, index, current_time, last_bar_time, last_bar_time_utc, index_hedge_name, mongo_db_v1):
        '''
        This runs the alphas based on time and if the V1 alphas have run
        :param index: 
        :param last_bar_time: 
        :param last_bar_time_utc: 
        :param index_hedge_name: 
        :return: 
        '''

        try:

            # must use current time to calculate session time because has current date
            alpha_sess_start, alpha_sess_decision, alpha_sess_exec, alpha_next_sess_date = index.session.get(
                current_time, 0)



            if not self.run_only_test_exos and (self.reset_exo_from_beginning or self.override_time_check_run_exo or last_bar_time >= alpha_sess_decision):
                alphas_list = list(self.mongo_db_v2['alpha_data'].find({'context.index_hedge_name': index_hedge_name},{'name':1,'context':1}))

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
                                earliest_date = last_bar_time.date()
                                for swarm in swarm_list:

                                    v1_alpha = mongo_db_v1['swarms'].find_one({'swarm_name': swarm},{'last_date':1})

                                    if v1_alpha['last_date'].date() < earliest_date:
                                        earliest_date = v1_alpha['last_date'].date()
                                        v1_alpha_ok = False

                                    if not v1_alpha_ok:
                                        last_bar_time_utc = self.time_to_utc_from_local_tz(datetime.combine(earliest_date, time(0, 0, 0)), index.session.tz.zone)


                        if not 'alpha_update_time' in alpha['context']:
                            self.run_alpha(alpha['name'], last_bar_time_utc)

                        else:
                            last_alpha_update_time = self.time_to_utc_from_none(alpha['context']['alpha_update_time'])
                            last_alpha_update_time = self.utc_to_time(last_alpha_update_time, index.session.tz.zone)


                            if self.reset_exo_from_beginning or self.override_time_check_run_exo:
                                self.run_alpha(alpha['name'], last_bar_time_utc)
                            elif last_alpha_update_time < alpha_sess_decision and v1_alpha_ok:
                                #check V1 alpha update
                                self.run_alpha(alpha['name'], last_bar_time_utc)
                                # print('running 3 ' + alpha['name'])
        except Exception as e:
            log.warning("Failed Alpha Check {0}".format(e))
            log.exception(e)


    def run_alpha(self, alpha_name, update_time):
        '''
        alpha run and save
        :param alpha_name: 
        :param update_time: 
        :return: 
        '''
        # try:

        self.mongo_db_v2['alpha_data'].update_one({'name': alpha_name},
                                                  {'$set': {'context.alpha_update_time': update_time}})

        if self.date_end is None:
            dm2 = DataManager()
        else:
            dm2 = DataManager(date_start=self.date_start, date_end=self.date_end)
        #print(alpha_name)

        try:
            '''C - compiled code, will not run on local machine'''
            saved_alpha = StrategyBase.load(dm2, alpha_name)
            saved_alpha.run()
            saved_alpha.save()

            self.mongo_db_v2['alpha_data'].update_one({'name': alpha_name},
                                                      {'$set': {'context.alpha_end_update_time': update_time}})
        except Exception as e:
            log.warning("Failed Alpha {0}".format(alpha_name))
            log.exception(e)
            self.signalapp_exo.send(
                MsgStatus('V2_Alpha', 'V2 Alpha Error {0}'.format(alpha_name), notify=True))

        #print('running finished ' + alpha_name)

        # self.mongo_db_v2['alpha_data'].update_one({'name': alpha_name},
        #                                           {'$set': {'context.alpha_end_update_time': update_time}})

        # self.signalapp_alpha.send(MsgStatus('V2_Alpha', 'V2 Alpha finished {0}'.format(alpha_name), notify=True))

        # self.run_account_positions_process()

        #log.warn('running finished ' + alpha_name)

        # except:

    def get_campaign_alpha_list(self):
        '''
        this gets the full list of alphas that the current active campaigns use
        :return: the list of alphas that the campaigns use
        '''

        # mongo_client_v1 = MongoClient(MONGO_CONNSTR_V1)
        # mongo_db_v1 = mongo_client_v1[MONGO_EXO_DB_V1]



        # pipeline = [
        #     {
        #         '$lookup':
        #             {
        #                 'from': 'campaigns',
        #                 'localField': 'campaign_name',
        #                 'foreignField': 'name',
        #                 'as': 'alphas'
        #             }
        #     },
        #     {'$group': {'_id': '$campaign_name', 'alphas_list': {'$push': '$alphas'}}}
        #
        # ]
        # final_alpha_list = []
        #
        # try:
        #     for campaign_list in list(self.mongo_db_v1['accounts'].aggregate(pipeline)):
        #
        #         for alpha_list in list(campaign_list['alphas_list'][0][0]['alphas']):
        #             alpha_list_replace = alpha_list.replace('!NEW_', "")
        #             final_alpha_list.append(alpha_list_replace)
        # except Exception as e:
        #     log.warning(e)

        full_alpha_list = []

        try:
            campaign_names = list(self.mongo_db_v1['accounts'].distinct('campaign_name'))
            campaign_list = list(self.mongo_db_v1['campaigns_smart'].find({'name': {'$in': campaign_names}}))

            for campaign in campaign_list:
                alpha_list = SmartCampaignBase.get_alphas_list_from_settings(campaign)
                full_alpha_list = list(set(full_alpha_list) | set(alpha_list))

            full_alpha_list = [word.replace('!NEW_', "") for word in full_alpha_list]

        except Exception as e:
            log.warning(e)

        # full_alpha_list

        return full_alpha_list

    def get_campaign_exo_list(self, final_alpha_list):
        '''
        this gets the full list of exos that the current active campaigns use
        :return: the list of exos that the campaigns use
        '''

        exo_list = []

        try:
            alpha_list_mongo = self.mongo_db_v2['alpha_data'].find({'name': {'$in': final_alpha_list}}, {'context': 1})

            for alpha in alpha_list_mongo:
                exo_list.append(alpha['context']['index_hedge_name'])
                if 'index_passive_name' in alpha['context']:
                    exo_list.append(alpha['context']['index_passive_name'])

        except Exception as e:
            log.warning(e)

        return exo_list

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
            log.warning(e)
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
    igs = IndexGenerationScript(instrument='US.CL')
    igs.run_main_index_alpha_script()








