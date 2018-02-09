from tmqrscripts.tweet.get_account_position_tweet import AccountPositionTweet
from tmqrscripts.tweet.send_tweet import Tweet_System
import time
from tmqr.logs import log

class RunningAccountTweet:
    def __init__(self):
        log.setup('scripts', 'CampaignMessageUpdate', to_file=True)
        log.info('Running Account Tweet')
        self.apt = AccountPositionTweet()
        self.ts = Tweet_System()

    def run_through_accounts(self, campaign_name, product_in, current_time_local):
        # print(campaign_name)
        accounts_list = self.apt.get_accounts(campaign_name)
        print(accounts_list)
        for account in accounts_list:
            print(account)

            ap_current = self.apt.get_accounts_positions_mongo(account['name'])

            loop_count = 0
            account_time = ap_current['date_now']
            # print('time compare',account_time, current_time_local)
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
    rat = RunningAccountTweet()
    rat.run_through_accounts('SmartCampaign_Diversified_Str_Top_select_','ES')