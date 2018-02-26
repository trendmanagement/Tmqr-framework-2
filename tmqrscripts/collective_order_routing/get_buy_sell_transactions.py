import os
import numpy as np
import pandas as pd
# import pytz
from pymongo import MongoClient
import pymongo
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tmqrscripts.collective_order_routing.order_routing import Collective2_Order_Routing, ORDER_ACTIONS, INSTRUMENT_TYPE, ORDER_CMD
from datetime import timedelta  # datetime, time,
from tmqr.settings import *

from tmqr.logs import log


class OrderGeneration:
    month_symbols = {
        1:'F',
        2:'G',
        3:'H',
        4:'M'
    }
    def __init__(self):
        log.setup('scripts', 'OrderGeneration', to_file=True)
        log.info('Running Order Generation')

        mongo_client_v1 = MongoClient(MONGO_CONNSTR_V1)
        self.mongo_db_v1 = mongo_client_v1[MONGO_EXO_DB_V1]

        mongo_client_v2 = MongoClient(MONGO_CONNSTR)
        self.mongo_db_v2 = mongo_client_v2[MONGO_DB]

        self.query_time = datetime.now()

    def get_accounts(self, campaign_name):
        # campaign_list_dict = list(self.mongo_db_v1['campaigns_smart'].find({},{'name':1}))
        # campaign_list = []
        # for cmp in campaign_list_dict:
        #     campaign_list.append(cmp['name'])
        # return list(self.mongo_db_v1['accounts'].find({'campaign_name':{'$in': campaign_list}}))
        return list(self.mongo_db_v1['accounts'].find({'campaign_name': campaign_name, 'c2': True}))

    def get_accounts_positions_mongo(self, account_name):
        return list(self.mongo_db_v1['accounts_positions'].find({'name': account_name}))[0]

    def get_accounts_positions_archive_mongo(self, account_name):
        return list(self.mongo_db_v1['accounts_positions_archive'].find({'name': account_name}).sort('date_now',
                                                                                                     pymongo.DESCENDING).limit(
            1))[0]

    def get_smart_campaign(self, campaign_name):
        return list(self.mongo_db_v1['campaigns_smart'].find({'name': campaign_name}))[0]

    def get_instrument_list_from_smartcampaign(self, smart_campaign):
        # print(smart_campaign)

        product_list = []
        for alpha_name, alpha_settings in smart_campaign['alphas'].items():
            # print(alpha_settings['product'])
            if alpha_settings['product'] not in product_list:
                product_list.append(alpha_settings['product'])

        # instrument_list = list(product_dict)
        # print('instrument_list',instrument_list)
        # print(product_list)
        instruments = list(self.mongo_db_v1['instruments'].find({'exchangesymbol': {'$in': list(product_list)}}))

        final_product_list = {}
        for instrument in instruments:
            # print(instrument)
            final_product_list[instrument['exchangesymbol']] = instrument

        return final_product_list



    def generate_future_symbol(self, c2_symbol, product):
        month = product['asset']['month']
        year = product['asset']['year']%10
        return f'{c2_symbol}{month}{year}'



    def calc_transactions(self, instrument, accounts_positions, accounts_positions_archive):

        # orders_rows = ""
        position_dict = {}
        transaction_list = []

        for position in accounts_positions_archive['positions']:
            if position['asset']['idinstrument'] == instrument['idinstrument']:

                if position['asset']['_type'] == 'opt':
                    key = (position['asset']['_type'], position['asset']['idcontract'], position['asset']['idoption'])
                else:
                    key = (position['asset']['_type'], position['asset']['idcontract'])

                if key not in position_dict:
                    position_dict[key] = position
                    position_dict[key]['final_position'] = 0

                    position_dict[key]['before_transaction_position'] = 0
                    position_dict[key]['after_transaction_position'] = 0


                position_dict[key]['final_position'] += position['qty']

                #fill position_dict[key]['before_transaction_position']
                position_dict[key]['before_transaction_position'] = position_dict[key]['final_position']



        for position in accounts_positions['positions']:
            if position['asset']['idinstrument'] == instrument['idinstrument']:

                if position['asset']['_type'] == 'opt':
                    key = (position['asset']['_type'], position['asset']['idcontract'], position['asset']['idoption'])
                else:
                    key = (position['asset']['_type'], position['asset']['idcontract'])

                if key not in position_dict:
                    position_dict[key] = position
                    position_dict[key]['final_position'] = 0

                    position_dict[key]['before_transaction_position'] = 0
                    position_dict[key]['after_transaction_position'] = 0


                position_dict[key]['final_position'] -= position['qty']

                position_dict[key]['after_transaction_position'] += position['qty']

        # now negate any final position and that will be the order
        for key, value in position_dict.items():
            print(value)
            if value['final_position'] != 0:

                if value['after_transaction_position'] == 0:
                    '''closing of a position'''
                    if value['before_transaction_position'] < 0:
                        '''Buy to close'''
                        order = {
                            'value':value,
                            'ORDER_CMD':ORDER_CMD.SIGNAL.value,
                            'ORDER_ACTIONS':ORDER_ACTIONS.BUY_TO_CLOSE.value,
                            'quantity':abs(value['before_transaction_position'])
                        }

                        transaction_list.append(order)
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_CLOSE.value, abs(value['before_transaction_position'])))
                    elif value['before_transaction_position'] > 0:
                        '''Sell to close'''

                        order = {
                            'value': value,
                            'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                            'ORDER_ACTIONS': ORDER_ACTIONS.SELL_TO_CLOSE.value,
                            'quantity': value['before_transaction_position']
                        }

                        transaction_list.append(order)

                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_CLOSE.value, value['before_transaction_position']))

                elif value['before_transaction_position'] != 0 and \
                    np.sign(value['after_transaction_position']) \
                        != np.sign(value['before_transaction_position']):
                    '''there is closing of a position and opening of a new one'''

                    if value['after_transaction_position'] > 0:
                        # '''Buy to close'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_CLOSE.value, abs(value['before_transaction_position'])))
                        # '''Buy to open'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_OPEN.value, value['after_transaction_position']))

                        order = {
                            'value': value,
                            'ORDER_CMD': ORDER_CMD.REVERSE.value,
                            'ORDER_ACTIONS': None,
                            'quantity': value['after_transaction_position']
                        }

                        transaction_list.append(order)

                    else:
                        # '''Sell to close'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_CLOSE.value, value['before_transaction_position']))
                        # '''Sell to open'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_OPEN.value, abs(value['after_transaction_position'])))

                        order = {
                            'value': value,
                            'ORDER_CMD': ORDER_CMD.REVERSE.value,
                            'ORDER_ACTIONS': None,
                            'quantity': abs(value['after_transaction_position'])
                        }

                        transaction_list.append(order)

                elif value['before_transaction_position'] != 0 and \
                    np.sign(value['after_transaction_position']) \
                        == np.sign(value['before_transaction_position']):
                    '''there is closing of a position and opening of a new one'''

                    if value['after_transaction_position'] > 0:
                        # '''Buy to close'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_CLOSE.value, abs(value['before_transaction_position'])))
                        # '''Buy to open'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_OPEN.value, value['after_transaction_position']))
                        if value['after_transaction_position'] - value['before_transaction_position'] > 0:
                            # buying more orders
                            order = {
                                'value': value,
                                'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                                'ORDER_ACTIONS': ORDER_ACTIONS.BUY_TO_OPEN.value,
                                'quantity': value['after_transaction_position'] - value['before_transaction_position']
                            }

                            transaction_list.append(order)
                        else:
                            # sell to close long orders
                            order = {
                                'value': value,
                                'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                                'ORDER_ACTIONS': ORDER_ACTIONS.SELL_TO_CLOSE.value,
                                'quantity': abs(value['after_transaction_position'] - value['before_transaction_position'])
                            }

                            transaction_list.append(order)


                    else:
                        # '''Sell to close'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_CLOSE.value, value['before_transaction_position']))
                        # '''Sell to open'''
                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_OPEN.value, abs(value['after_transaction_position'])))
                        if value['after_transaction_position'] - value['before_transaction_position'] < 0:
                            order = {
                                'value': value,
                                'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                                'ORDER_ACTIONS': ORDER_ACTIONS.SELL_TO_OPEN.value,
                                'quantity': abs(
                                    value['after_transaction_position'] - value['before_transaction_position'])
                            }

                            transaction_list.append(order)

                        else:

                            order = {
                                'value': value,
                                'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                                'ORDER_ACTIONS': ORDER_ACTIONS.BUY_TO_CLOSE.value,
                                'quantity': abs(
                                    value['after_transaction_position'] - value['before_transaction_position'])
                            }

                            transaction_list.append(order)


                elif value['before_transaction_position'] == 0 and value['after_transaction_position'] != 0:
                    '''opening of a new position'''
                    if value['after_transaction_position'] > 0:
                        '''Buy to open'''

                        order = {
                            'value': value,
                            'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                            'ORDER_ACTIONS': ORDER_ACTIONS.BUY_TO_OPEN.value,
                            'quantity': value['after_transaction_position']
                        }

                        transaction_list.append(order)

                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.BUY_TO_OPEN.value, value['after_transaction_position']))
                    else:
                        '''Sell to open'''

                        order = {
                            'value': value,
                            'ORDER_CMD': ORDER_CMD.SIGNAL.value,
                            'ORDER_ACTIONS': ORDER_ACTIONS.SELL_TO_OPEN.value,
                            'quantity': abs(value['after_transaction_position'])
                        }

                        transaction_list.append(order)

                        # transaction_list.append(
                        #     (value, ORDER_ACTIONS.SELL_TO_OPEN.value, abs(value['after_transaction_position'])))


        return transaction_list