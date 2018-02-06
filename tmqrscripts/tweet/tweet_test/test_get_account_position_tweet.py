import unittest
from tmqrscripts.tweet.get_account_position_tweet import AccountPositionTweet
from tmqrscripts.tweet.send_tweet import Tweet_System
import time

class Test_AccountPositionTweet(unittest.TestCase):
    def setUp(self):
        print('In setUp()')
        self.apt = AccountPositionTweet()
        self.test_account = 'SmartCampaign_Diversified_Str_Concept_NO_GC'

    def tearDown(self):
        print('In tearDown()')
        del self.apt

    def test_get_accounts_positions_mongo(self):

        ap = self.apt.get_accounts_positions_mongo(self.test_account)
        self.assertNotEqual([],ap)

    def test_get_smart_campaign(self):
        self.assertNotEqual(0, self.apt.risk_free_rate)

        ap = self.apt.get_accounts_positions_mongo(self.test_account)
        sc = self.apt.get_smart_campaign(ap['campaign_name'])
        self.assertIn('name',sc,'name is not in smartcampaign')

    def test_get_product_dict(self):

        self.assertNotEqual(0, self.apt.risk_free_rate)

        ap = self.apt.get_accounts_positions_mongo(self.test_account)
        sc = self.apt.get_smart_campaign(ap['campaign_name'])
        # print(sc['name'])
        product_dict = self.apt.get_instrument_list_from_smartcampaign(sc)

        print(product_dict)
        self.assertNotEqual([], product_dict)


        # self.apt.calc_payoff(self.test_account,ap,)

    def test_get_product_dict(self):
        ap_current = self.apt.get_accounts_positions_mongo(self.test_account)
        ap_archive = self.apt.get_accounts_positions_archive_mongo(self.test_account)
        sc = self.apt.get_smart_campaign(ap_current['campaign_name'])
        # print(sc['name'])
        product_dict = self.apt.get_instrument_list_from_smartcampaign(sc)

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
                message = '#{}__{}'.format(product['exchangesymbol'],ap_current['name'],ap_current['campaign_name'])

                # self.apt.calc_payoff(self.test_account, product, ap_current, ap_archive)

                ts.post_tweets_with_image(message=message,
                                      img=self.apt.calc_payoff(self.test_account, product, ap_current, ap_archive))

            # time.sleep(5)

    # def test_run_imgkit(self):
    #     # self.apt.run_imgkit()
    #     pass

    def test_get_accounts_positions_archive_mongo(self):
        ap = self.apt.get_accounts_positions_archive_mongo(self.test_account)
        print(ap)

    def test_transactions(self):
        # ap_current = self.apt.get_accounts_positions_mongo(self.test_account)
        # ap_archive = self.apt.get_accounts_positions_archive_mongo(self.test_account)
        #
        # sc = self.apt.get_smart_campaign(ap_current['campaign_name'])
        # # print(sc['name'])
        # product_dict = self.apt.get_instrument_list_from_smartcampaign(sc)
        #
        # self.apt.calc_transactions(product_dict[21], ap_current, ap_archive)
        pass