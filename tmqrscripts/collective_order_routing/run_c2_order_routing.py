import unittest
from tmqrscripts.collective_order_routing.order_routing \
    import Collective2_Order_Routing, ORDER_ACTIONS, INSTRUMENT_TYPE, ORDER_DURATION_TYPE, ORDER_CMD
from tmqrscripts.collective_order_routing.get_buy_sell_transactions import OrderGeneration
import time
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

        accounts_list = self.apt.get_accounts(campaign_name)
        print(accounts_list)
        for account in accounts_list:
            print(account)

            ap_current = self.apt.get_accounts_positions_mongo(account['name'])

            loop_count = 0
            account_time = ap_current['date_now']


            log.info(
                f"Running Account Tweet {campaign_name}: {product_in} : messagetime{current_time_local} : account_time{account_time}")
            while account_time < current_time_local and loop_count < 10:

                time.sleep(10)
                ap_current = self.apt.get_accounts_positions_mongo(account['name'])
                account_time = ap_current['date_now']
                loop_count+=1
                log.info(
                    f"Looping Running Account Tweet {campaign_name}: {product_in} : messagetime{current_time_local} : account_time{account_time} : loopcount{loop_count}")

            ap_archive = self.apt.get_accounts_positions_archive_mongo(account['name'])
            sc = self.apt.get_smart_campaign(ap_current['campaign_name'])
            product_dict = self.apt.get_instrument_list_from_smartcampaign(sc)

            product = product_dict[product_in]

            message = '#{}__{}'.format(product['exchangesymbol'],ap_current['name'],ap_current['campaign_name'])

            self.ts.post_tweets_with_image(message=message,
                                  img=self.apt.calc_payoff(account['name'], product, ap_current, ap_archive))


if __name__ == "__main__":
    rat = RunningC2OrderRouting()
    rat.run_through_accounts('SmartCampaign_Diversified_Str_Top_select_','ES')