from tmqrscripts.tweet.get_account_position_tweet import AccountPositionTweet
from tmqrscripts.tweet.send_tweet import Tweet_System
import time

apt = AccountPositionTweet()
test_account = 'SmartCampaign_Diversified_Str_Concept_NO_GC'


ap_current = apt.get_accounts_positions_mongo(test_account)
ap_archive = apt.get_accounts_positions_archive_mongo(test_account)
sc = apt.get_smart_campaign(ap_current['campaign_name'])
# print(sc['name'])
product_dict = apt.get_instrument_list_from_smartcampaign(sc)

# self.apt.calc_payoff(self.test_account, product_dict[21], ap, )

# img = self.apt.calc_payoff(self.test_account, product_dict[21], ap, )

ts = Tweet_System()
# ts.post_tweets()
# ts.post_tweets(self.apt.calc_payoff(self.test_account, product_dict[21], ap, ))
# idinstrument = 21
# print(product_dict)
# ['CL', 'ZW', 'HE', 'NG', '6E', 'LE', 'ZC', '6J', 'GC', '6C', 'ZN', 'ES', 'ZS', '6B', 'ZL']
for id, product in product_dict.items():
    # print(id,product['exchangesymbol'])
    if id == 'CL':
        message = '#{}__{}'.format(product['exchangesymbol'], ap_current['name'], ap_current['campaign_name'])

        # self.apt.calc_payoff(self.test_account, product, ap_current, ap_archive)

        ts.post_tweets_with_image(message=message,
                                  img=apt.calc_payoff(test_account, product, ap_current, ap_archive))