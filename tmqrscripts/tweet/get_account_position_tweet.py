import os
import numpy as np
import pandas as pd
# import pytz
from pymongo import MongoClient
import pymongo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import timedelta #datetime, time,
from tmqr.settings import *
# from tqdm import tqdm_notebook
# from tmqrfeed import DataManager
# from tmqrfeed.contracts import ContractBase
# import pickle
# from smartcampaign import SmartCampaignBase
from exobuilder.algorithms.blackscholes import blackscholes, \
    blackscholes_greeks, blackscholes_gamma, blackscholes_vega, blackscholes_theta
import seaborn as sns
# import ipywidgets as widgets
# # from IPython.display import clear_output
# # from IPython.display import display, HTML
# import math
import PIL
import imgkit

from tmqr.logs import log

class AccountPositionTweet:
    def __init__(self):
        log.setup('scripts', 'TweetingScript', to_file=True)
        log.info('Running tweet script')

        mongo_client_v1 = MongoClient(MONGO_CONNSTR_V1)
        self.mongo_db_v1 = mongo_client_v1[MONGO_EXO_DB_V1]

        mongo_client_v2 = MongoClient(MONGO_CONNSTR)
        self.mongo_db_v2 = mongo_client_v2[MONGO_DB]

        self.query_time = datetime.now()

        self.risk_free_rate = self.get_risk_free_rate()

    def get_accounts(self, campaign_name):
        # campaign_list_dict = list(self.mongo_db_v1['campaigns_smart'].find({},{'name':1}))
        # campaign_list = []
        # for cmp in campaign_list_dict:
        #     campaign_list.append(cmp['name'])
        # return list(self.mongo_db_v1['accounts'].find({'campaign_name':{'$in': campaign_list}}))
        return list(self.mongo_db_v1['accounts'].find({'campaign_name':campaign_name, 'twitter':True}))

    def get_accounts_positions_mongo(self,account_name):
        return list(self.mongo_db_v1['accounts_positions'].find({'name':account_name}))[0]

    def get_accounts_positions_archive_mongo(self,account_name):
        return list(self.mongo_db_v1['accounts_positions_archive'].find({'name':account_name}).sort('date_now',pymongo.DESCENDING).limit(1))[0]

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

    def get_risk_free_rate(self):
        try:
            return list(
                self.mongo_db_v2['quotes_riskfreerate'].find({}, projection={'last_rfr': True}))[0]['last_rfr']
        except:
            return 0.01

    def _format_position_table(self):

        table_template = """
            <div style="font-family:sans-serif, Verdana, Geneva;">
                
                <div style="display: inline-block; border: 1px solid; float: left;">{2}</div>
                    <div style="display: inline-block; border: 1px solid;">
                    <div>Current Future Price : {5}</div>
                    <div>Current ~P/L From Previous Settle : {6}</div>
                    <div>Delta : {3}</div>
                    <div>Gamma : {4}</div>
                    <div>Vega  : {8}</div>
                    <div>Theta : {9}</div>
                </div> 
                <div style="clear: both; display: block;">
                    <h4>Positions at {1} for {7}</h4>
                    <div style="display: inline-block; border: 1px solid;">
                        <table border="0" cellpadding="10" width="100%">
                        <thead>
                        <tr>
                            <th style="text-align: center;">Asset</th>
                            <th style="text-align: center;">Underlying Yesterday Settle</th>
                            <th style="text-align: center;">Current Price</th>
                            <th style="text-align: center;">Qty</th>
                            <th style="text-align: center;">IV</th>
                            <th style="text-align: center;">Delta</th>
                            <th style="text-align: center;">Gamma</th>
                            <th style="text-align: center;">To Expiration</th>
                        </tr>
                        </thead>
                        {0}
                        </table>
                    </div>
                </div>
                <div>
                {10}
                </div>
            </div>
            """
        return table_template

    def _format_position_row(self, asset, underlying, settle, qty, iv, delta, gamma, days_to_expiration, instrument):
        row_template = '''
        <tr>
            <td>{asset}</td>
            <td style="text-align: center;">{underlying}</td>
            <td style="text-align: center;">{settle}</td>
            <td style="text-align: center; {qty_style}">{qty}</td>
            <td style="text-align: right;">{iv}</td> 
            <td style="text-align: right;">{delta}</td>
            <td style="text-align: right;">{gamma}</td>
            <td style="text-align: right;">{days_to_expiration} days</td>
        </tr>
        '''
        def qty_color(qty):
            if qty < 0:
                return 'color: #CC3327;'
            if qty > 0:
                return 'color: #28CC52;'
            return ''

        def format_price(asset, instrument, price):
            if asset.startswith('F.'):
                return round(price, len(str(instrument['ticksize'])) - 2)
            elif asset.startswith('C.') or asset.startswith('P.'):
                return round(price, len(str(instrument['optionticksize'])) - 2)
            return price

        def format_iv(iv):
            if np.isnan(iv):
                return ''
            return '{0:0.2f}%'.format(iv * 100)

        values_dict = {}
        values_dict['asset'] = asset
        values_dict['underlying'] = format_price('F.', instrument, underlying)
        values_dict['settle'] = format_price(asset, instrument, settle)
        values_dict['qty_style'] = qty_color(qty)
        values_dict['qty'] = qty
        values_dict['iv'] = format_iv(iv)
        values_dict['delta'] = format_iv(delta)
        values_dict['gamma'] = format_iv(gamma)
        values_dict['days_to_expiration'] = '{:.0f}'.format(days_to_expiration)

        return row_template.format(**values_dict)

    def _format_order_table(self):

        table_template = """
                <h4>Orders at {1} for {2}</h4>                
                <div style="display: inline-block; border: 1px solid;">
                    <table border="0" cellpadding="10" width="100%">
                    <thead>
                    <tr>
                        <th style="text-align: center;">Asset</th>
                        <th style="text-align: center;">Qty</th>
                        <th style="text-align: center;">Decision Time</th>
                        <th style="text-align: center;">Transaction Time</th>                        
                    </tr>
                    </thead>
                    {0}
                    </table>
                </div>
            """
        return table_template

    def _format_order_row(self, asset, qty, instrument):
        row_template = '''
        <tr>
            <td>{asset}</td>
            <td style="text-align: center; {qty_style}">{qty}</td>
            <td style="text-align: center;">{decision_time}</td>
            <td style="text-align: center;">{transaction_time}</td> 
        </tr>
        '''
        def qty_color(qty):
            if qty < 0:
                return 'color: #CC3327;'
            if qty > 0:
                return 'color: #28CC52;'
            return ''

        # def format_price(asset, instrument, price):
        #     if asset.startswith('F.'):
        #         return round(price, len(str(instrument['ticksize'])) - 2)
        #     elif asset.startswith('C.') or asset.startswith('P.'):
        #         return round(price, len(str(instrument['optionticksize'])) - 2)
        #     return price
        #
        # def format_iv(iv):
        #     if np.isnan(iv):
        #         return ''
        #     return '{0:0.2f}%'.format(iv * 100)

        values_dict = {}
        values_dict['asset'] = asset
        values_dict['qty_style'] = qty_color(qty)
        values_dict['qty'] = qty
        values_dict['decision_time'] = (instrument['customdayboundarytime'] \
                                       - timedelta(minutes=instrument['decisionoffsetminutes'])).time()
        values_dict['transaction_time'] = instrument['customdayboundarytime'].time()
        # values_dict['underlying'] = format_price('F.', instrument, underlying)
        # values_dict['settle'] = format_price(asset, instrument, settle)
        # values_dict['days_to_expiration'] = '{:.0f}'.format(days_to_expiration)

        return row_template.format(**values_dict)

    def add_to_payoff(self, temp_payoff, temp_delta, temp_payoff_ae, temp_delta_ae,
                      instrument_outputs):

        if instrument_outputs['payoff_val'].size == 0:
            instrument_outputs['payoff_val'] = np.array(temp_payoff)
        else:
            instrument_outputs['payoff_val'] = np.add(instrument_outputs['payoff_val'], temp_payoff)

        if instrument_outputs['delta_val'].size == 0:
            instrument_outputs['delta_val'] = np.array(temp_delta)
        else:
            instrument_outputs['delta_val'] = np.add(instrument_outputs['delta_val'], temp_delta)

        if instrument_outputs['payoff_val_ae'].size == 0:
            instrument_outputs['payoff_val_ae'] = np.array(temp_payoff_ae)
        else:
            instrument_outputs['payoff_val_ae'] = np.add(instrument_outputs['payoff_val_ae'], temp_payoff_ae)

        if instrument_outputs['delta_val_ae'].size == 0:
            instrument_outputs['delta_val_ae'] = np.array(temp_delta_ae)
        else:
            instrument_outputs['delta_val_ae'] = np.add(instrument_outputs['delta_val_ae'], temp_delta_ae)

        # return payoff_val, delta_val, payoff_val_ae, delta_val_ae

    # def blackscholes_gamma(self, ulprice, strike, toexpiry, riskfreerate, iv):
    #     d1 = (math.log(ulprice / strike) + (riskfreerate + iv * iv / 2) * toexpiry) / (iv * math.sqrt(toexpiry))
    #     nd = math.exp(-d1 * d1 / 2) / 2.5066282746310002
    #
    #     return nd / (ulprice * iv * math.sqrt(toexpiry))

    def option_price(self, callorput, underlyingprice, strike, to_expiration_years, iv, riskfreerate=0.01, option_price_return_type = 1):
        '''
        option_price_return_type = 1 returns price only
        option_price_return_type = 2 returns prices and deltas at current price and expiration
        option_price_return_type = 3 returns everything
        '''

        if option_price_return_type == 1:
            return blackscholes(callorput, underlyingprice, strike, \
                                to_expiration_years, riskfreerate, iv)
        if option_price_return_type == 2:
            return blackscholes(callorput, underlyingprice, strike, \
                                to_expiration_years, riskfreerate, iv), \
                   blackscholes_greeks(callorput, underlyingprice, strike, to_expiration_years, riskfreerate, iv), \
                   blackscholes(callorput, underlyingprice, strike, \
                                0, riskfreerate, iv), \
                   blackscholes_greeks(callorput, underlyingprice, strike, 0, riskfreerate, iv),
        else:
            return blackscholes(callorput, underlyingprice, strike, \
                                to_expiration_years, riskfreerate, iv), \
                   blackscholes_greeks(callorput, underlyingprice, strike, to_expiration_years, riskfreerate, iv), \
                   blackscholes(callorput, underlyingprice, strike, \
                                0, riskfreerate, iv), \
                   blackscholes_greeks(callorput, underlyingprice, strike, 0, riskfreerate, iv), \
                   blackscholes_gamma(underlyingprice, strike, to_expiration_years, riskfreerate, iv),\
                   blackscholes_vega(underlyingprice, strike, to_expiration_years, riskfreerate, iv),\
                   blackscholes_theta(callorput, underlyingprice, strike, to_expiration_years, riskfreerate, iv),



    def fill_future(self, position, future_dict, instrument):
        # print('fill_future',position['asset']['idcontract'],future_dict)
        if position['asset']['idcontract'] not in future_dict:
            future = list(self.mongo_db_v1['futures_contract_settlements'] \
                          .find({'idcontract': position['asset']['idcontract'], \
                                 'date': {'$lte': self.query_time}}) \
                          .sort([('date', pymongo.DESCENDING)]).limit(1))

            if len(future) > 0:
                future_dict[position['asset']['idcontract']] = future[0]

                future_current = list(self.mongo_db_v1['contracts_bars'] \
                              .find({'idcontract': position['asset']['idcontract'], \
                                     'datetime': {'$lte': self.query_time}}) \
                              .sort([('datetime', pymongo.DESCENDING)]).limit(1))

                '''set up transaction time'''

                future_dict[position['asset']['idcontract']]['future_transaction'] = None
                future_dict[position['asset']['idcontract']]['future_transaction_time'] = None

                trans_time = datetime.combine(self.query_time.date(), instrument['customdayboundarytime'].time())

                if self.query_time >= trans_time:
                    future_transaction = list(self.mongo_db_v1['contracts_bars'] \
                                          .find({'idcontract': position['asset']['idcontract'], \
                                                 'datetime': {'$lte': trans_time}}) \
                                          .sort([('datetime', pymongo.DESCENDING)]).limit(1))

                    if len(future_transaction) > 0:
                        future_dict[position['asset']['idcontract']]['future_transaction'] = future_transaction[0]
                        future_dict[position['asset']['idcontract']]['future_transaction_time'] = trans_time


                if len(future_current) > 0:
                    # future_dict[position['asset']['idcontract']] = future[0]

                    future_dict[position['asset']['idcontract']]['current_bar'] = future_current[0]

                    current_future_close = future_dict[position['asset']['idcontract']]['current_bar']['close']
                    # settle = future_dict[position['asset']['idcontract']]['close']
                    # print('ticksize',instrument['ticksize'])
                    future_dict[position['asset']['idcontract']]['payoff_price_series'] = \
                        np.linspace(current_future_close - 50.0 * instrument['optionstrikeincrement'], \
                                    current_future_close - 1.0 * instrument['ticksize'], 100)

                    future_dict[position['asset']['idcontract']]['payoff_price_series'] = \
                        np.append(future_dict[position['asset']['idcontract']]['payoff_price_series'], current_future_close)

                    future_dict[position['asset']['idcontract']]['payoff_price_series'] = \
                        np.append(future_dict[position['asset']['idcontract']]['payoff_price_series'], ( \
                            np.linspace(current_future_close + 1.0 * instrument['ticksize'], \
                                        current_future_close + 50.0 * instrument['optionstrikeincrement'], 100)))

    def fill_future_payoff_output_row(self, position, future_dict, instrument,
                                      instrument_outputs, qty):
        if qty != None:
            '''adds the future to the payoff and delta calculations because qty is not equal to 0'''
            # print('payoff_price_series',future_dict[position['asset']['idcontract']]['payoff_price_series'])
            # print('close',future_dict[position['asset']['idcontract']]['current_bar']['close'])
            temp_payoff = (future_dict[position['asset']['idcontract']]['payoff_price_series'] - \
                           future_dict[position['asset']['idcontract']]['current_bar']['close']) \
                          / instrument['ticksize'] \
                          * instrument['tickvalue'] * qty

            temp_delta = np.ones(len(temp_payoff))

            self.add_to_payoff(temp_payoff, temp_delta, temp_payoff, temp_delta,
                               instrument_outputs)

            instrument_outputs['total_settle_delta'].append(position['qty'])

            instrument_outputs['output_rows'] += self._format_position_row(position['asset']['contractname'], \
                                                          future_dict[position['asset']['idcontract']]['settlement'], \
                                                          future_dict[position['asset']['idcontract']]['current_bar']['close'], \
                                                          position['qty'], 0.0, \
                                                          position['qty'], 0, \
                                                          0, instrument)

    def calc_pl(self, accounts_positions, instrument_outputs, instrument, is_archive):

        for position in accounts_positions['positions']:
            if position['asset']['idinstrument'] == instrument['idinstrument']:

                if position['asset']['_type'] == 'opt':

                    if position['asset']['idoption'] not in instrument_outputs['option_dict']:
                        option = list(self.mongo_db_v1['options_data']
                                        .find({'idoption': position['asset']['idoption'], \
                                            'datetime': {'$lte': self.query_time}}) \
                                        .sort([('datetime', pymongo.DESCENDING)]).limit(1))

                        if len(option) > 0:
                            instrument_outputs['option_dict'][position['asset']['idoption']] = option[0]

                    self.fill_future(position, instrument_outputs['future_dict'], instrument)

                    start_future_price = None
                    end_future_price = None
                    if is_archive:
                        start_future_price = instrument_outputs['future_dict'][position['asset']['idcontract']]['settlement']
                        end_future_price = instrument_outputs['future_dict'][position['asset']['idcontract']]['current_bar']['close']
                        if instrument_outputs['future_dict'][position['asset']['idcontract']]['future_transaction_time'] != None:
                            end_future_price = instrument_outputs['future_dict'][position['asset']['idcontract']]['future_transaction']['close']

                    elif instrument_outputs['future_dict'][position['asset']['idcontract']]['future_transaction_time'] != None:
                        start_future_price = \
                            instrument_outputs['future_dict'][position['asset']['idcontract']] \
                                ['future_transaction']['close']
                        end_future_price = \
                            instrument_outputs['future_dict'][position['asset']['idcontract']]['current_bar']['close']


                    if True:#position['qty'] != 0:
                        if start_future_price != None and end_future_price != None:

                            option = instrument_outputs['option_dict'][position['asset']['idoption']]

                            start_option_price = self.option_price( \
                                    position['asset']['callorput'],
                                    start_future_price,
                                    position['asset']['strikeprice'],
                                    option['timetoexpinyears'],
                                    option['impliedvol'],
                                    riskfreerate=self.risk_free_rate,
                                    option_price_return_type=1)

                            end_option_price = self.option_price( \
                                    position['asset']['callorput'],
                                    end_future_price,
                                    position['asset']['strikeprice'],
                                    option['timetoexpinyears'],
                                    option['impliedvol'],
                                    riskfreerate=self.risk_free_rate,
                                    option_price_return_type=1)

                            instrument_outputs['total_pl'].append((end_option_price - start_option_price) / instrument['optionticksize'] \
                                                             * instrument['optiontickvalue'] * position['qty'])


                        #####################################################

                        if not is_archive:
                            option = instrument_outputs['option_dict'][position['asset']['idoption']]

                            end_future_price = \
                                instrument_outputs['future_dict'][position['asset']['idcontract']]['current_bar'][
                                    'close']

                            end_option_price, end_delta_option, end_option_ae, end_delta_option_ae, end_gamma_option, \
                                end_vega_option, end_theta_option = self.option_price( \
                                    position['asset']['callorput'],
                                    end_future_price,
                                    position['asset']['strikeprice'],
                                    option['timetoexpinyears'],
                                    option['impliedvol'],
                                    riskfreerate=self.risk_free_rate,
                                    option_price_return_type=3)

                            instrument_outputs['output_rows'] += self._format_position_row(
                                position['asset']['optionname'], \
                                    instrument_outputs['future_dict'][position['asset']['idcontract']]['settlement'], \
                                    end_option_price, position['qty'], option['impliedvol'], \
                                    end_delta_option[0] * position['qty'], end_gamma_option, \
                                    option['timetoexpinyears'] * 365, instrument)

                            instrument_outputs['total_settle_delta'].append(end_delta_option[0] * position['qty'])

                            instrument_outputs['total_gamma'].append(end_gamma_option)
                            instrument_outputs['total_vega'].append(end_vega_option)
                            instrument_outputs['total_theta'].append(end_theta_option)

                            option_pnl = []
                            option_delta = []
                            option_pnl_ae = []
                            option_delta_ae = []
                            for underlying_price in instrument_outputs['future_dict'][position['asset']['idcontract']][
                                'payoff_price_series']:
                                price_payoff, delta_payoff, price_ae, delta_ae = self.option_price(
                                    position['asset']['callorput'], \
                                    underlying_price, \
                                    position['asset'][
                                        'strikeprice'], \
                                    option['timetoexpinyears'],
                                    option['impliedvol'],
                                    riskfreerate=self.risk_free_rate,
                                    option_price_return_type=2)

                                option_pnl.append( \
                                    (price_payoff - end_option_price) / instrument['optionticksize'] * instrument[
                                        'optiontickvalue'] * \
                                    position['qty'])

                                option_delta.append( \
                                    delta_payoff[0] * position['qty'])

                                option_pnl_ae.append( \
                                    (price_ae - end_option_ae) / instrument['optionticksize'] * instrument[
                                        'optiontickvalue'] * \
                                    position['qty'])

                                option_delta_ae.append( \
                                    delta_ae[0] * position['qty'])

                                # payoff_val, delta_val, payoff_val_ae, delta_val_ae = \
                            self.add_to_payoff(option_pnl, option_delta, option_pnl_ae, option_delta_ae,
                                                       instrument_outputs)
                        #####################################################

                else:
                    self.fill_future(position, instrument_outputs['future_dict'], instrument)

                    start_future_price = None
                    end_future_price = None
                    if is_archive:
                        start_future_price = instrument_outputs['future_dict'][position['asset']['idcontract']][
                            'settlement']
                        end_future_price = \
                            instrument_outputs['future_dict'][position['asset']['idcontract']]['current_bar']['close']

                        if instrument_outputs['future_dict'][position['asset']['idcontract']]['future_transaction_time'] != None:
                            end_future_price = \
                                instrument_outputs['future_dict'][position['asset']['idcontract']]['future_transaction'][
                                    'close']
                    elif instrument_outputs['future_dict'][position['asset']['idcontract']][
                                     'future_transaction_time'] != None:
                        start_future_price = \
                            instrument_outputs['future_dict'][position['asset']['idcontract']] \
                                ['future_transaction']['close']
                        end_future_price = \
                            instrument_outputs['future_dict'][position['asset']['idcontract']]['current_bar']['close']

                    if position['qty'] != 0 and start_future_price != None and end_future_price != None:
                        instrument_outputs['total_pl'].append((end_future_price - start_future_price) \
                              / instrument['ticksize'] \
                              * instrument['tickvalue'] * position['qty'])

                    if not is_archive:
                        self.fill_future_payoff_output_row(position, instrument_outputs['future_dict'], instrument,
                                                       instrument_outputs, position['qty'])

    def calc_payoff(self, account_name, instrument, accounts_positions, accounts_positions_archive):

        instrument_outputs = {}
        instrument_outputs['payoff_val'] = np.array([])
        instrument_outputs['delta_val'] = np.array([])
        instrument_outputs['payoff_val_ae'] = np.array([])
        instrument_outputs['delta_val_ae'] = np.array([])

        instrument_outputs['total_settle_delta'] = [];
        instrument_outputs['total_gamma'] = []
        instrument_outputs['total_vega'] = []
        instrument_outputs['total_theta'] = []

        instrument_outputs['total_pl'] = []

        instrument_outputs['output_rows'] = ""

        instrument_outputs['future_dict'] = {}
        instrument_outputs['option_dict'] = {}

        self.calc_pl(accounts_positions_archive, instrument_outputs, instrument, True)
        self.calc_pl(accounts_positions, instrument_outputs, instrument, False)


        # for position in accounts_positions['positions']:
        #     if position['asset']['idinstrument'] == instrument['idinstrument']:
        #
        #         if position['asset']['_type'] == 'opt':
        #
        #             if position['asset']['idoption'] not in instrument_outputs['option_dict']:
        #                 option = list(self.mongo_db_v1['options_data']
        #                                 .find({'idoption': position['asset']['idoption'], \
        #                                     'datetime': {'$lte': self.query_time}}) \
        #                                 .sort([('datetime', pymongo.DESCENDING)]).limit(1))
        #
        #                 if len(option) > 0:
        #                     instrument_outputs['option_dict'][position['asset']['idoption']] = option[0]
        #
        #             self.fill_future(position, instrument_outputs['future_dict'], instrument)
        #
        #             option = instrument_outputs['option_dict'][position['asset']['idoption']]
        #
        #             settle_option, settle_delta_option, settle_ae, settle_delta_ae, settle_gamma_option, \
        #                 settle_vega_option, settle_theta_option = self.option_price( \
        #                     position['asset']['callorput'],
        #                     instrument_outputs['future_dict'][position['asset']['idcontract']]['settlement'],
        #                     position['asset']['strikeprice'],
        #                     option['timetoexpinyears'],
        #                     option['impliedvol'],
        #                     riskfreerate=self.risk_free_rate,
        #                     return_more_greeks=True)
        #
        #             instrument_outputs['output_rows'] += self._format_position_row(position['asset']['optionname'], \
        #                             instrument_outputs['future_dict'][position['asset']['idcontract']]['settlement'], \
        #                             settle_option, position['qty'], option['impliedvol'], \
        #                             settle_delta_option[0] * position['qty'], settle_gamma_option, \
        #                             option['timetoexpinyears'] * 365, instrument)
        #
        #             if position['qty'] != 0:
        #
        #                 instrument_outputs['total_settle_delta'].append(settle_delta_option[0] * position['qty'])
        #
        #                 instrument_outputs['total_gamma'].append(settle_gamma_option)
        #                 instrument_outputs['total_vega'].append(settle_vega_option)
        #                 instrument_outputs['total_theta'].append(settle_theta_option)
        #
        #                 option_pnl = []
        #                 option_delta = []
        #                 option_pnl_ae = []
        #                 option_delta_ae = []
        #                 for underlying_price in instrument_outputs['future_dict'][position['asset']['idcontract']]['payoff_price_series']:
        #                     price_payoff, delta_payoff, price_ae, delta_ae = self.option_price(position['asset']['callorput'], \
        #                                                                                 underlying_price, \
        #                                                                                 position['asset'][
        #                                                                                     'strikeprice'], \
        #                                                                                 option['timetoexpinyears'],
        #                                                                                 option['impliedvol'],
        #                                                                                 riskfreerate=self.risk_free_rate,
        #                                                                                 return_more_greeks=False)
        #
        #                     option_pnl.append( \
        #                         (price_payoff - settle_option) / instrument['optionticksize'] * instrument[
        #                             'optiontickvalue'] * \
        #                         position['qty'])
        #
        #                     option_delta.append( \
        #                         delta_payoff[0] * position['qty'])
        #
        #                     option_pnl_ae.append( \
        #                         (price_ae - settle_ae) / instrument['optionticksize'] * instrument[
        #                             'optiontickvalue'] * \
        #                         position['qty'])
        #
        #                     option_delta_ae.append( \
        #                         delta_ae[0] * position['qty'])
        #
        #
        #
        #                 # payoff_val, delta_val, payoff_val_ae, delta_val_ae = \
        #                 self.add_to_payoff(option_pnl, option_delta, option_pnl_ae, option_delta_ae,
        #                                        instrument_outputs)
        #
        #
        #
        #         else:
        #             self.fill_future(position, instrument_outputs['future_dict'], instrument)
        #
        #             self.fill_future_payoff_output_row(position, instrument_outputs['future_dict'], instrument,
        #                                                      instrument_outputs, position['qty'])

        log.info('start of image manipulation')

        f, (ax1, ax2) = plt.subplots(2, gridspec_kw={'height_ratios': [3, 1]});

        log.info('created sub plots')

        future_settle = instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['settlement']
        # future_settle = future_dict[list(future_dict)[0]]['close']

        future_close = instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['current_bar']['close']

        # print('payoff_price_series', len(instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['payoff_price_series']), len(instrument_outputs['payoff_val']))

        payoff_percent = pd.DataFrame()
        payoff_percent['Future Price'] = instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['payoff_price_series']
        payoff_percent['Payoff Current'] = instrument_outputs['payoff_val'].round(2)

        price_moves_percent = [0.97, 0.98, 0.99, 1, 1.01, 1.02, 1.03]

        percent_changes = []
        df_index = []
        for percent in price_moves_percent:
            percent_changes.append('{}%'.format(round((percent - 1) * 100)))
            df_index.append(payoff_percent.loc[payoff_percent['Future Price'] >= percent * future_close].index[0])


        payoff_percent_final = payoff_percent.loc[df_index].copy()
        payoff_percent_final['Percentage Changes'] = percent_changes
        payoff_percent_final.set_index('Percentage Changes', inplace=True)

        payoff_df = pd.DataFrame()
        payoff_df['Future Price'] = instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['payoff_price_series']
        payoff_df['Payoff Current'] = instrument_outputs['payoff_val']
        payoff_df['Payoff Expiration'] = instrument_outputs['payoff_val_ae']
        payoff_df.set_index('Future Price', inplace=True)

        #calculates the current p/l from settlement
        # print('test1',payoff_df.index[np.searchsorted(payoff_df.index, future_close)])
        # future_close_idx = payoff_df.index[np.searchsorted(payoff_df.index, future_close)]
        # print('test',payoff_df['Payoff Current'].loc[future_close_idx])

        log.info('going to plot payoff')

        payoff_df.plot(ax=ax1)
        # print('close',instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['current_bar']['close'])

        plt.axes(ax1)
        plt.axvline(x=future_close, ymin=0, ymax=1, color='red')

        log.info('plotted payoff')

        delta_df = pd.DataFrame()
        delta_df['Future Price'] = instrument_outputs['future_dict'][list(instrument_outputs['future_dict'])[0]]['payoff_price_series']
        delta_df['Delta Current'] = instrument_outputs['delta_val']
        delta_df['Delta Expiration'] = instrument_outputs['delta_val_ae']
        delta_df.set_index('Future Price', inplace=True)
        delta_df.plot(ax=ax2)
        plt.axes(ax2)
        plt.axvline(x=future_close, ymin=0, ymax=1, color='red')

        log.info('saving payoff image')

        payoff_image = 'payoff.jpg'
        f.savefig(payoff_image)
        log.info('saved payoff image')

        # print(payoff_percent_final.to_html(border=0))
        # print('pl', instrument_outputs['total_pl'], sum(instrument_outputs['total_pl']))

        options = {"xvfb": ""}
        table_image = 'tables.jpg'
        imgkit.from_string(self._format_position_table()
                           .format(instrument_outputs['output_rows'],
                                   self.query_time.date(),
                                   payoff_percent_final.to_html(border=0),
                                   round(sum(instrument_outputs['total_settle_delta']),4),
                                   round(sum(instrument_outputs['total_gamma']),4),
                                   future_close,#future price
                                   round(sum(instrument_outputs['total_pl']), 4), #round(payoff_df['Payoff Current'].loc[future_close_idx], 4),
                                   instrument['exchangesymbol'],
                                   round(sum(instrument_outputs['total_vega']), 4),
                                   round(sum(instrument_outputs['total_theta']), 4),
                                   self.calc_transactions(instrument, accounts_positions, accounts_positions_archive)),
                           table_image,options =options)


        # order_table_image = 'order_table.jpg'
        # imgkit.from_string(self.calc_transactions(instrument, accounts_positions, accounts_positions_archive), order_table_image)

        table_path = '{}/{}'.format(os.getcwd(),table_image)
        # order_table_path = '{}/{}'.format(os.getcwd(), order_table_image)
        payoff_path = '{}/{}'.format(os.getcwd(), payoff_image)
        list_im = [table_path, payoff_path]

        imgs = [PIL.Image.open(i) for i in list_im]
        widths, heights = zip(*(i.size for i in imgs))

        img_merge = np.vstack((np.asarray(i.resize((min(widths),min(heights)), PIL.Image.ANTIALIAS)) for i in imgs))
        img_merge = PIL.Image.fromarray(img_merge)
        combined_img = 'combined_image.jpg'
        img_merge.save(combined_img)

        plt.close('all')

        return '{}/{}'.format(os.getcwd(), combined_img)

    def calc_transactions(self, instrument, accounts_positions, accounts_positions_archive):

        orders_rows = ""
        position_dict = {}

        for position in accounts_positions_archive['positions']:
            if position['asset']['idinstrument'] == instrument['idinstrument']:

                if position['asset']['_type'] == 'opt':
                    key = (position['asset']['_type'],position['asset']['idcontract'],position['asset']['idoption'])
                else:
                    key = (position['asset']['_type'], position['asset']['idcontract'])

                if key not in position_dict:
                    position_dict[key] = position
                    position_dict[key]['final_position'] = position['qty']

                else:
                    position_dict[key]['final_position'] += position['qty']


        for position in accounts_positions['positions']:
            if position['asset']['idinstrument'] == instrument['idinstrument']:

                if position['asset']['_type'] == 'opt':
                    key = (position['asset']['_type'],position['asset']['idcontract'],position['asset']['idoption'])
                else:
                    key = (position['asset']['_type'], position['asset']['idcontract'])

                if key not in position_dict:
                    position_dict[key] = position
                    position_dict[key]['final_position'] = -position['qty']
                else:
                    position_dict[key]['final_position'] -= position['qty']


        #now negate any final position and that will be the order
        for key, value in position_dict.items():
            if value['final_position'] != 0:
                # print('final_position',value['final_position'])
                if value['asset']['_type'] == 'opt':
                    orders_rows += self._format_order_row(value['asset']['optionname'], -value['final_position'],
                                           instrument)
                else:
                    orders_rows += self._format_order_row(value['asset']['contractname'], -value['final_position'],
                                                          instrument)

        return self._format_order_table().format(orders_rows,self.query_time.date(),
                                   instrument['exchangesymbol'])
