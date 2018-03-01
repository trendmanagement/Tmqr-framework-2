import unittest
from tmqrscripts.collective_order_routing.order_routing \
    import Collective2_Order_Routing, ORDER_ACTIONS, INSTRUMENT_TYPE, ORDER_DURATION_TYPE, ORDER_CMD
from tmqrscripts.collective_order_routing.get_buy_sell_transactions import OrderGeneration
import time
from tmqr.settings import *

'''
https://support.collective2.com/hc/en-us/articles/203005654-How-do-I-setup-C2-s-Signal-Entry-API-
https://collective2.com/api-docs/latest
https://trade.collective2.com/c2-futures-symbols/?
http://www.collective2.com/cgi-perl/signal.mpl?[PARAMETERS]
'''

class Test_AccountPositionC2Orders(unittest.TestCase):
    def setUp(self):
        print('In setUp()')
        self.test_account = 'SmartCampaign_JPlusA_Futures_Only_SmartC'
        self.og = OrderGeneration()
        self.cor = Collective2_Order_Routing(systemid=COLLECTIVE2_SYSTEMID, api_key=COLLECTIVE2_API_KEY, pwd=COLLECTIVE2_PWD)

    def tearDown(self):
        print('In tearDown()')
        del self.cor

    def test_generate_order_params(self):
        order_params = self.cor.generate_future_order_params(
            cmd=ORDER_CMD.SIGNAL.value,
            instrument_type='future', action=ORDER_ACTIONS.BUY_TO_OPEN.value, quantity=15, symbol='@ESH8', duration='DAY')

        self.assertEqual(order_params['cmd'],'signal')

    def test_generate_future_symbol(self):

        product = {
            'asset':{'month':'J',
                     'year':2018}
        }
        symbol = self.og.generate_future_symbol('AA',product)

        self.assertEqual(symbol,'AAJ8')

    def test_get_system_roster(self):
        ok = self.cor.get_system_roster()

        self.assertEqual(ok, "1")


    # def test_position_status(self):
    #     # ap_archive = { 'positions':[{
    #     #     'asset':{
    #     #         'idinstrument':21,
    #     #         '_type':'fut',
    #     #         'month':'J',
    #     #         'idcontract':4725,
    #     #         'contractname':'F.CLEJ18',
    #     #         'year':2018,
    #     #     },
    #     #     'qty':1
    #     #     }]
    #     # }
    #     #
    #     # ap = {
    #     #     'positions': []
    #     # }
    #
    #     product = {
    #         'asset': {'month': 'J',
    #                   'year': 2018}
    #     }
    #     symbol = self.og.generate_future_symbol('QCL', product)
    #
    #     return_message = self.cor.position_status_request(symbol)
    #
    #     print('order_request', return_message)

    # def xxxxsend_closing_orders(self):
    #     ap_archive = { 'positions':[{
    #         'asset':{
    #             'idinstrument':21,
    #             '_type':'fut',
    #             'month':'J',
    #             'idcontract':4725,
    #             'contractname':'F.CLEJ18',
    #             'year':2018,
    #         },
    #         'qty':1
    #         }]
    #     }
    #
    #     ap = {
    #         'positions': []
    #     }
    #
    #     self.send_testing_order(ap_archive, ap)
    #
    # def xxxxsend_opening_orders(self):
    #     ap = {'positions': [{
    #         'asset': {
    #             'idinstrument': 21,
    #             '_type': 'fut',
    #             'month': 'J',
    #             'idcontract': 4725,
    #             'contractname': 'F.CLEJ18',
    #             'year': 2018,
    #         },
    #         'qty': 3
    #     }]
    #     }
    #
    #     ap_archive = {
    #         'positions': []
    #     }
    #
    #     self.send_testing_order(ap_archive, ap)
    #
    # def xxx_reverse_orders(self):
    #     ap_archive = {'positions': [{
    #         'asset': {
    #             'idinstrument': 21,
    #             '_type': 'fut',
    #             'month': 'J',
    #             'idcontract': 4725,
    #             'contractname': 'F.CLEJ18',
    #             'year': 2018,
    #         },
    #         'qty': 0
    #     }]
    #     }
    #
    #     ap = {'positions': [{
    #         'asset': {
    #             'idinstrument': 21,
    #             '_type': 'fut',
    #             'month': 'J',
    #             'idcontract': 4725,
    #             'contractname': 'F.CLEJ18',
    #             'year': 2018,
    #         },
    #         'qty': -2
    #     }]
    #     }
    #
    #     self.send_testing_order(ap_archive,ap)

    # def send_testing_order(self,ap_archive,ap):
    #     sc = self.og.get_smart_campaign(self.test_account)
    #     product_dict = self.og.get_instrument_list_from_smartcampaign(sc)
    #
    #     for id, product in product_dict.items():
    #         # print(id,product['exchangesymbol'])
    #         if 'c2_symbol' in product and id == 'CL':
    #             transaction_list = self.og.calc_transactions(instrument=product,
    #                                                          accounts_positions=ap,
    #                                                          accounts_positions_archive=ap_archive)
    #
    #             print(transaction_list)
    #
    #             for transaction in transaction_list:
    #                 if transaction['value']['asset']['_type'] == 'fut':
    #                     print(transaction['value'], transaction['ORDER_CMD'],
    #                           transaction['ORDER_ACTIONS'], transaction['quantity'])
    #
    #                     symbol = self.og.generate_future_symbol(product['c2_symbol'],
    #                                                             transaction['value'])
    #
    #                     print(symbol)
    #
    #                     order_params = self.cor.generate_future_order_params(
    #                         cmd=transaction['ORDER_CMD'],
    #                         instrument_type=INSTRUMENT_TYPE.FUTURE.value,
    #                         action=transaction['ORDER_ACTIONS'],
    #                         quantity=transaction['quantity'],
    #                         symbol=symbol,
    #                         duration=ORDER_DURATION_TYPE.DAY_ORDER.value)
    #
    #                     print(order_params)
    #
    #                     return_message = self.cor.send_futures_order(order_params)
    #
    #                     print('order_request', return_message)
    #
    #                     self.assertIsNotNone(return_message)

    # def test_send_order(self):
    #     order_params = self.cor.generate_order_params(
    #         instrument=INSTRUMENT_TYPE.STOCK.value, action=ORDER_ACTIONS.SELL_TO_CLOSE.value, quantity=15, symbol='IBM', duration='DAY')
    #
    #     order_request = self.cor.send_futures_order(order_params)
    #
    #     print('order_request',order_request)
    #
    #     self.assertIsNotNone(order_request)

    # def test_get_product_dict(self):
    #     ap_current = self.og.get_accounts_positions_mongo(self.test_account)
    #     ap_archive = self.og.get_accounts_positions_archive_mongo(self.test_account)
    #
    #
    #
    #     sc = self.og.get_smart_campaign(ap_current['campaign_name'])
    #     # print(sc['name'])
    #     product_dict = self.og.get_instrument_list_from_smartcampaign(sc)
    #
    #     for id, product in product_dict.items():
    #         # print(id,product['exchangesymbol'])
    #         if  'c2_symbol' in product and id == 'CL':
    #             transaction_list = self.og.calc_transactions(instrument=product,
    #                                       accounts_positions=ap_current,
    #                                       accounts_positions_archive=ap_archive)
    #
    #             # message = '#{}__{}'.format(product['exchangesymbol'],ap_current['name'],ap_current['campaign_name'])
    #
    #             # self.apt.calc_payoff(self.test_account, product, ap_current, ap_archive)
    #
    #             print(transaction_list)
    #
    #             for transaction in transaction_list:
    #                 if transaction[0]['asset']['_type'] == 'fut':
    #                     print(transaction[0],transaction[1],transaction[2])
    #
    #                     symbol = self.og.generate_future_symbol(product['c2_symbol'], transaction[0])
    #
    #                     print(symbol)
    #
    #                     order_params = self.cor.generate_order_params(instrument_type=INSTRUMENT_TYPE.FUTURE.value,
    #                                                    action=transaction[1],
    #                                                    quantity=transaction[2],
    #                                                    symbol=symbol,
    #                                                    duration=ORDER_DURATION_TYPE.DAY_ORDER.value)
    #
    #                     print(order_params)
    #
    #                     order_request = self.cor.send_futures_order(order_params)
    #
    #                     print('order_request', order_request)
    #
    #                     self.assertIsNotNone(order_request)
