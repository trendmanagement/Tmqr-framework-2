import unittest
from tmqrscripts.collective_order_routing.order_routing \
    import Collective2_Order_Routing, ORDER_ACTIONS, INSTRUMENT_TYPE, ORDER_DURATION_TYPE, ORDER_CMD
from tmqrscripts.collective_order_routing.get_buy_sell_transactions import OrderGeneration
import time
from datetime import datetime, timedelta
from tmqr.settings import *
from tmqr.logs import log

class RunningC2OrderRouting:
    def __init__(self):
        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)
        log.info('Running Collective2_Order_Routing Script')
        self.og = OrderGeneration()
        self.cor = Collective2_Order_Routing(COLLECTIVE2_SYSTEMID, COLLECTIVE2_PWD)

    def run_through_accounts(self, campaign_name, product_in, current_time_local):
        log.setup('scripts', 'Collective2_Order_Routing', to_file=True)

        accounts_list = self.og.get_accounts(campaign_name)
        print(accounts_list)
        for account in accounts_list:
            print(account)

            ap_current = self.og.get_accounts_positions_mongo(account['name'])

            loop_count = 0
            account_time = ap_current['date_now']

            log.info(
                f"Running Account Tweet {campaign_name}: {product_in} : messagetime{current_time_local} : account_time{account_time}")
            while account_time < current_time_local and loop_count < 10:

                time.sleep(10)
                ap_current = self.og.get_accounts_positions_mongo(account['name'])
                account_time = ap_current['date_now']
                loop_count+=1
                log.info(
                    f"Looping Running Account Tweet {campaign_name}: {product_in} : messagetime{current_time_local} : account_time{account_time} : loopcount{loop_count}")

            ap_archive = self.og.get_accounts_positions_archive_mongo(account['name'])



            sc = self.og.get_smart_campaign(ap_current['campaign_name'])
            product_dict = self.og.get_instrument_list_from_smartcampaign(sc)

            product = product_dict[product_in]

            transaction_list = self.og.calc_transactions(instrument=product,
                                                         accounts_positions=ap_current,
                                                         accounts_positions_archive=ap_archive)

            for transaction in transaction_list:
                if transaction['value']['asset']['_type'] == 'fut' and 'c2_symbol' in product:
                    print(transaction['value'], transaction['ORDER_CMD'],
                          transaction['ORDER_ACTIONS'], transaction['quantity'])

                    symbol = self.og.generate_future_symbol(product['c2_symbol'],
                                                            transaction['value'])

                    print(symbol)

                    order_params = self.cor.generate_future_order_params(
                        cmd=transaction['ORDER_CMD'],
                        instrument_type=INSTRUMENT_TYPE.FUTURE.value,
                        action=transaction['ORDER_ACTIONS'],
                        quantity=transaction['quantity'],
                        symbol=symbol,
                        duration=ORDER_DURATION_TYPE.DAY_ORDER.value)

                    print(order_params)

                    return_message = self.cor.send_futures_order(order_params)

                    print('order_request', return_message)

                    # self.assertIsNotNone(return_message)

            # message = '#{}__{}'.format(product['exchangesymbol'],ap_current['name'],ap_current['campaign_name'])

            # self.ts.post_tweets_with_image(message=message,
            #                       img=self.apt.calc_payoff(account['name'], product, ap_current, ap_archive))


if __name__ == "__main__":
    rat = RunningC2OrderRouting()
    rat.run_through_accounts('SmartCampaign_JPlusA_Futures_Only_SmartC','ES',datetime.now()- timedelta(hours=5, minutes=10))