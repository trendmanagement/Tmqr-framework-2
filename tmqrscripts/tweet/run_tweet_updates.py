from tmqrscripts.tweet.get_account_position_tweet import AccountPositionTweet
from tmqrscripts.tweet.send_tweet import Tweet_System

class RunningAccountTweet:
    def __init__(self):
        self.apt = AccountPositionTweet()
        self.ts = Tweet_System()

    def run_through_accounts(self, campaign_name, product_in):
        print(campaign_name)
        accounts_list = self.apt.get_accounts(campaign_name)
        print(accounts_list)
        for account in accounts_list:
            print(account)

            ap_current = self.apt.get_accounts_positions_mongo(account['name'])
            ap_archive = self.apt.get_accounts_positions_archive_mongo(account['name'])
            sc = self.apt.get_smart_campaign(ap_current['campaign_name'])
            product_dict = self.apt.get_instrument_list_from_smartcampaign(sc)

            product = product_dict[product_in]
            # for id, product in product_dict.items():
                # print(id,product['exchangesymbol'])
            #     if id == product_in:
            message = '#{}__{}'.format(product['exchangesymbol'],ap_current['name'],ap_current['campaign_name'])

            self.ts.post_tweets_with_image(message=message,
                                  img=self.apt.calc_payoff(account['name'], product, ap_current, ap_archive))


if __name__ == "__main__":
    rat = RunningAccountTweet()
    rat.run_through_accounts('SmartCampaign_Diversified_Str_Top_select_','ES')